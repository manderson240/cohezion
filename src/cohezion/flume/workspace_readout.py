"""Sparse-code workspace readout over latent vectors.

Wraps :class:`~cohezion.flume.sparse_analysis.SparseLatentAnalysis` as the canonical
"global workspace" readout for FLUME-style latents: which learned dictionary atoms
are active in a thought vector, and swapping the top-k atoms between two vectors.

Experimental grounding (2026-08-02, vault research/2026-08-01-flume-sparse-workspace-design.md):
pre-registered 3-arm test on 3,170 corpus docs — swapping 8-16 learned atoms transfers
retrievable semantic identity 71.5-88.5% (96% at k=64) while the identical edit with a
random dictionary transfers 0%; held-out-dictionary replication HOLDS (A1(16)=0.82).

Contracts (advisor-reviewed 2026-08-02):
  * ``swap`` is a STATISTICAL operation — experimentally validated transfer, not a
    deterministic semantic guarantee. Treat outputs as approximations.
  * Single-owner: one consumer owns an instance; no cross-thread mutation guarantees.
  * Fail-open: ``read`` returns ``None`` (never raises) until a dictionary is fitted;
    a failing fit leaves the readout unfitted and clears the buffer.
  * The observe buffer is HARD-CAPPED at ``auto_fit_after`` and cleared after every
    fit attempt (success or failure) — no unbounded growth.
  * Persistence is dictionary-only (``save``/``load``); the observe buffer is
    intentionally transient across restarts.

Wire-at-Creation target: ``JourneyTracker.track_execution`` (workspace_readout kwarg)
annotates ``TrajectoryPoint.metadata["workspace_atoms"]``.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from cohezion.flume.sparse_analysis import SparseLatentAnalysis


logger = logging.getLogger(__name__)


class WorkspaceReadout:
    """Self-activating sparse-code readout: observe latents, auto-fit, then read/swap.

    Hot-path cost contract (adversarial review, measured 2026-08-02): dictionary
    fitting takes ~65s at 256x2048 — with ``fit_in_background=True`` (default) it
    runs on a daemon thread and never blocks the caller. ``read()`` costs a
    bounded ~27ms (lasso_lars solve) per call once fitted — comparable to the
    optional embedding call in the same JourneyTracker path; callers needing
    lower latency should annotate post-hoc instead.
    """

    _MAX_FIT_ATTEMPTS = 3  # review finding: a persistently failing fit must not stall forever

    def __init__(
        self,
        auto_fit_after: int = 256,
        n_atoms: int = 512,
        sparsity_target: float = 0.05,
        *,
        fit_in_background: bool = True,
        _force_numpy: bool = False,
    ) -> None:
        self._auto_fit_after = max(2, auto_fit_after)
        self._sla = SparseLatentAnalysis(
            n_atoms=n_atoms, sparsity_target=sparsity_target, _force_numpy=_force_numpy
        )
        self._buffer: list[np.ndarray] = []
        self._fit_in_background = fit_in_background
        self._fit_thread: threading.Thread | None = None
        self._fit_attempts = 0

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_fitted(self) -> bool:
        return self._sla._dictionary is not None

    def _install_dictionary(self, dictionary: np.ndarray) -> None:
        """Install a pre-built dictionary (tests / load path)."""
        self._sla._dictionary = np.asarray(dictionary, dtype=float)

    # ------------------------------------------------------------------
    # Accumulation + auto-fit
    # ------------------------------------------------------------------

    def observe(self, z: np.ndarray) -> None:
        """Accumulate a latent; fit the dictionary once the buffer reaches threshold.

        Non-blocking: with ``fit_in_background`` the fit runs on a daemon thread
        (observations during an in-flight fit are dropped). After the first
        successful fit, further observations are no-ops (the dictionary is frozen
        for this instance's lifetime; refit = new instance). After
        ``_MAX_FIT_ATTEMPTS`` failed fits the readout stops accumulating — a
        persistently failing fit must not re-stall the caller forever.
        """
        if self.is_fitted:
            return
        if self._fit_thread is not None and self._fit_thread.is_alive():
            return  # fit in flight: drop, don't buffer behind it
        if self._fit_attempts >= self._MAX_FIT_ATTEMPTS:
            return  # retry cap reached: permanently inert (fail-open)
        self._buffer.append(np.asarray(z, dtype=float).ravel())
        if len(self._buffer) < self._auto_fit_after:
            return
        buffered = self._buffer[:]
        self._buffer.clear()  # hard cap: cleared on every fit attempt
        self._fit_attempts += 1
        if self._fit_in_background:
            self._fit_thread = threading.Thread(
                target=self._fit_batch, args=(buffered,), daemon=True
            )
            self._fit_thread.start()
        else:
            self._fit_batch(buffered)

    def _fit_batch(self, buffered: list[np.ndarray]) -> None:
        try:
            # np.stack inside the try: mixed-dimension latents must fail open too
            self._sla.fit(np.stack(buffered))
        except Exception as exc:  # fail-open: stay unfitted, re-accumulate
            logger.warning("WorkspaceReadout fit failed (fail-open): %s", exc)

    # ------------------------------------------------------------------
    # Readout
    # ------------------------------------------------------------------

    def read(self, z: np.ndarray, k: int = 16) -> list[tuple[int, float]] | None:
        """Top-k (atom_id, weight) pairs by |weight|, or None while unfitted.

        Never raises: any encoding failure returns None.
        """
        if not self.is_fitted:
            return None
        try:
            return self._sla.top_features(np.asarray(z, dtype=float).ravel(), k=k)
        except Exception as exc:
            logger.warning("WorkspaceReadout read failed (fail-open): %s", exc)
            return None

    def swap(self, z_a: np.ndarray, z_b: np.ndarray, k: int = 16) -> np.ndarray:
        """Replace z_a's top-k atom content with z_b's top-k atom content.

        Statistical, experimentally validated (see module docstring) — NOT a
        deterministic semantic guarantee. Raises RuntimeError while unfitted
        (swap is an explicit operation; callers must check ``is_fitted``).
        """
        D = self._sla._dictionary
        if D is None:
            raise RuntimeError("WorkspaceReadout.swap requires a fitted dictionary")
        za = np.asarray(z_a, dtype=float).ravel()
        zb = np.asarray(z_b, dtype=float).ravel()
        ca = self._sla.encode(za)
        cb = self._sla.encode(zb)
        ta = np.argsort(np.abs(ca))[::-1][:k]
        tb = np.argsort(np.abs(cb))[::-1][:k]
        return za - D[ta].T @ ca[ta] + D[tb].T @ cb[tb]

    # ------------------------------------------------------------------
    # Persistence (dictionary only — buffer is transient by contract)
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        D = self._sla._dictionary
        if D is None:
            raise RuntimeError("Nothing to save: dictionary not fitted")
        np.savez_compressed(Path(path), D=D)

    def load(self, path: str | Path) -> None:
        """Atomically replace the dictionary from ``path`` (single-owner contract)."""
        self._install_dictionary(np.load(Path(path))["D"])
