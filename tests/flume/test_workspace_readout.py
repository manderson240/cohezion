"""Tests for WorkspaceReadout — sparse-code workspace readout over latent vectors.

Validated experimentally 2026-08-02 (vault research/2026-08-01-flume-sparse-workspace-design.md):
swapping top-k learned dictionary atoms transfers semantic identity (82-96%) while
random-dictionary atoms transfer ~0%. This suite encodes the mechanism as unit-scale
discriminating tests plus the JourneyTracker consumption invariant.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.flume.workspace_readout import WorkspaceReadout


def _synthetic_sparse_latents(
    rng: np.random.RandomState, n_samples: int = 300, n_atoms: int = 24, dim: int = 32
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Latents generated as sparse nonneg combos of a ground-truth dictionary.

    Returns (latents, ground_truth_dict, dominant_atom_per_sample).
    """
    D_true = rng.randn(n_atoms, dim)
    D_true /= np.linalg.norm(D_true, axis=1, keepdims=True)
    Z, dom = [], []
    for _ in range(n_samples):
        atoms = rng.choice(n_atoms, size=3, replace=False)
        weights = np.array([3.0, 0.5, 0.25])
        Z.append((weights[:, None] * D_true[atoms]).sum(axis=0))
        dom.append(atoms[0])
    return np.array(Z), D_true, np.array(dom)


class TestStructural:
    def test_api_surface(self):
        r = WorkspaceReadout(auto_fit_after=8)
        assert hasattr(r, "observe")
        assert hasattr(r, "read")
        assert hasattr(r, "swap")
        assert hasattr(r, "save")
        assert hasattr(r, "load")
        assert r.is_fitted is False

    def test_read_returns_none_before_fit(self):
        r = WorkspaceReadout(auto_fit_after=100)
        assert r.read(np.zeros(16)) is None


class TestAutoFit:
    def test_observe_triggers_fit_at_threshold(self):
        rng = np.random.RandomState(0)
        Z, _, _ = _synthetic_sparse_latents(rng, n_samples=40)
        r = WorkspaceReadout(auto_fit_after=32, n_atoms=16, _force_numpy=True, fit_in_background=False)
        for i in range(31):
            r.observe(Z[i])
        assert r.is_fitted is False  # discriminating: below threshold stays unfitted
        r.observe(Z[31])
        assert r.is_fitted is True

    def test_buffer_cleared_after_fit(self):
        rng = np.random.RandomState(1)
        Z, _, _ = _synthetic_sparse_latents(rng, n_samples=40)
        r = WorkspaceReadout(auto_fit_after=16, n_atoms=8, _force_numpy=True, fit_in_background=False)
        for z in Z[:20]:
            r.observe(z)
        assert len(r._buffer) == 0  # advisor finding: buffer must not grow unbounded

    def test_mixed_dimension_latents_fail_open(self):
        """Mixed-dim latents at the fit threshold must not raise (advisor/self-review
        finding 2026-08-02: np.stack outside the try violated the fail-open contract)."""
        r = WorkspaceReadout(auto_fit_after=3, _force_numpy=True, fit_in_background=False)
        r.observe(np.zeros(8))
        r.observe(np.zeros(8))
        r.observe(np.zeros(16))  # triggers fit attempt over mismatched shapes
        assert r.is_fitted is False
        assert len(r._buffer) == 0  # buffer still cleared (hard cap holds)

    def test_fit_failure_is_fail_open(self):
        r = WorkspaceReadout(auto_fit_after=4, _force_numpy=True, fit_in_background=False)
        # degenerate all-zero latents can break dictionary learning; must not raise
        for _ in range(6):
            r.observe(np.zeros(8))
        assert r.read(np.zeros(8)) is None or isinstance(r.read(np.zeros(8)), list)


class TestHotPathContract:
    """Adversarial-review findings 2026-08-02: the fit must never block the caller,
    and a persistently failing fit must not re-stall forever."""

    def test_background_fit_does_not_block_observe(self, monkeypatch):
        import threading
        import time

        r = WorkspaceReadout(auto_fit_after=4, n_atoms=8, _force_numpy=True)
        release = threading.Event()
        fitted = threading.Event()

        def slow_fit(batch):
            release.wait(timeout=10)
            r._sla._dictionary = np.eye(8)
            fitted.set()

        monkeypatch.setattr(r._sla, "fit", slow_fit)
        t0 = time.monotonic()
        for _ in range(4):
            r.observe(np.random.RandomState(0).randn(8))
        elapsed = time.monotonic() - t0
        assert elapsed < 1.0  # discriminating: a synchronous fit would block 10s here
        assert r.is_fitted is False  # fit still in flight
        release.set()
        assert fitted.wait(timeout=5)
        r._fit_thread.join(timeout=5)
        assert r.is_fitted is True

    def test_retry_cap_stops_refit_attempts(self, monkeypatch):
        r = WorkspaceReadout(auto_fit_after=2, n_atoms=8, _force_numpy=True, fit_in_background=False)
        calls = {"n": 0}

        def failing_fit(batch):
            calls["n"] += 1
            raise ValueError("boom")

        monkeypatch.setattr(r._sla, "fit", failing_fit)
        for _ in range(20):
            r.observe(np.zeros(8))
        # discriminating: without the cap, 20 observations at threshold 2 = 10 fit
        # attempts; the cap must hold it at _MAX_FIT_ATTEMPTS and stop buffering.
        assert calls["n"] == WorkspaceReadout._MAX_FIT_ATTEMPTS
        assert len(r._buffer) == 0


class TestReadAndSwap:
    @pytest.fixture()
    def fitted(self):
        rng = np.random.RandomState(42)
        Z, _d_true, dom = _synthetic_sparse_latents(rng)
        # sklearn path — the coder the experiment validated (numpy MP at this
        # sparsity allows only 1 active atom and cannot express the swap)
        r = WorkspaceReadout(
            auto_fit_after=len(Z), n_atoms=24, sparsity_target=0.05, fit_in_background=False
        )
        for z in Z:
            r.observe(z)
        assert r.is_fitted
        return r, Z, dom, rng

    def test_read_returns_sorted_topk(self, fitted):
        r, Z, _, _ = fitted
        out = r.read(Z[0], k=5)
        assert isinstance(out, list) and len(out) == 5
        mags = [abs(w) for _, w in out]
        assert mags == sorted(mags, reverse=True)

    def test_read_never_raises_on_garbage(self, fitted):
        r, _, _, _ = fitted
        assert r.read(np.zeros(32)) is not None  # zero vector: degenerate but safe

    def test_swap_transfers_identity_better_than_random_dict(self, fitted):
        """The validated mechanism at unit scale: learned-dict swap moves z_a toward
        z_b's identity; the SAME edit with a random dictionary must not. A wrong
        implementation (ignoring the dictionary, or editing nothing) fails one side."""
        r, Z, _dom, rng = fitted
        rand = WorkspaceReadout(auto_fit_after=10**9, n_atoms=24, sparsity_target=0.05)
        Dr = rng.randn(24, Z.shape[1])
        rand._install_dictionary(Dr / np.linalg.norm(Dr, axis=1, keepdims=True))

        pairs = [(i, i + 150) for i in range(0, 40)]
        learned_hits = rand_hits = 0
        for a, b in pairs:
            for readout, bucket in ((r, "learned"), (rand, "rand")):
                z_new = readout.swap(Z[a], Z[b], k=3)
                # identity check: is the swapped vector closer to z_b than to z_a?
                d_a = np.linalg.norm(z_new - Z[a])
                d_b = np.linalg.norm(z_new - Z[b])
                if d_b < d_a:
                    if bucket == "learned":
                        learned_hits += 1
                    else:
                        rand_hits += 1
        assert learned_hits >= 0.7 * len(pairs)
        assert learned_hits >= rand_hits + 0.2 * len(pairs)

    def test_save_load_roundtrip(self, fitted, tmp_path):
        r, Z, _, _ = fitted
        p = tmp_path / "ws.npz"
        r.save(p)
        r2 = WorkspaceReadout(auto_fit_after=10**9, sparsity_target=0.05)
        r2.load(p)
        assert r2.is_fitted
        a = r.read(Z[0], k=4)
        b = r2.read(Z[0], k=4)
        assert [i for i, _ in a] == [i for i, _ in b]


class TestJourneyTrackerConsumption:
    """W-series consumption invariant: the tracker must READ the readout, not just hold it."""

    def _tracker(self, readout):
        from cohezion.compound.journey_tracker import JourneyTracker

        return JourneyTracker(workspace_readout=readout)

    def _result(self):
        from unittest.mock import MagicMock

        res = MagicMock()
        res.metrics = {"coherence": 0.7, "tier_used": "npu"}
        res.token_metrics = {"cache_hit_rate": 0.5}
        res.duration_seconds = 1.0
        res.success = True
        res.output = "ok"
        return res

    def test_metadata_annotated_when_fitted(self):
        rng = np.random.RandomState(7)
        r = WorkspaceReadout(auto_fit_after=32, n_atoms=16, _force_numpy=True, fit_in_background=False)
        for _ in range(32):
            r.observe(rng.randn(2048))
        assert r.is_fitted
        tracker = self._tracker(r)
        point = tracker.track_execution(self._result(), "solve the workspace task", "execution")
        atoms = point.metadata.get("workspace_atoms")
        assert atoms is not None and len(atoms) > 0  # discriminating: unwired tracker fails

    def test_no_readout_no_annotation(self):
        tracker = self._tracker(None)
        point = tracker.track_execution(self._result(), "solve the workspace task", "execution")
        assert "workspace_atoms" not in point.metadata

    def test_cb17_autocreate_injects_workspace_readout(self):
        """Producer wiring (review lens 3): the CB17 auto-created JourneyTracker must
        carry a WorkspaceReadout — neutralizing the injection fails this test."""
        from unittest.mock import MagicMock

        from cohezion.compound.executor import CompoundExecutor

        ex = CompoundExecutor(MagicMock(), enable_cycle_persistence=True)
        tracker = ex._journey_tracker
        assert tracker is not None
        assert tracker._workspace_readout is not None

    def test_unfitted_readout_observes_but_does_not_annotate(self):
        r = WorkspaceReadout(auto_fit_after=10**9, _force_numpy=True, fit_in_background=False)
        tracker = self._tracker(r)
        tracker.track_execution(self._result(), "solve the workspace task", "execution")
        assert len(r._buffer) == 1  # discriminating: tracker must feed the readout
