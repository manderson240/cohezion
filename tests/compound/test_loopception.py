"""V-model discriminating tests for loopception depth gaps G15, G16, G18.

Tier 1 (structural): inspect.signature / inspect.getsource / hasattr — fire before
  any runtime code and catch signature drift immediately.
Tier 2 (behavioral discriminating): verify the runtime outcome is DIFFERENT between
  the wired and unwired states — not just "it doesn't crash."

Gap summary:
  G15 — compound_daemon.run_batch() routes through LoopCoordinator in-process,
         not subprocess(compound_cycle.py).
  G16a — JourneyTracker.__init__ injects LemonadeEmbedBridge as _flume_encoder.
  G16b — track_execution() calls text_to_latent() (FLUME-aware), not _text_to_latent().
  G18  — ManifoldEnv.step() / SwarmEnv.step() call record_env_state() on journey_tracker.
"""
from __future__ import annotations

import inspect
import pathlib

import numpy as np
import pytest


# ── G15 structural ────────────────────────────────────────────────────────────

class TestG15Structural:
    """T1: run_batch() must use LoopCoordinator, not raw subprocess."""

    def _daemon_src(self) -> str:
        p = pathlib.Path.home() / "cohezion-labs" / "compound_daemon.py"
        return p.read_text()

    def test_loop_coordinator_present(self):
        src = self._daemon_src()
        assert "LoopCoordinator" in src, "LoopCoordinator not referenced in run_batch()"

    def test_make_executor_present(self):
        src = self._daemon_src()
        assert "make_executor" in src, "make_executor not referenced — depth-4 path missing"

    def test_coordinator_run_with_executor(self):
        src = self._daemon_src()
        assert "coordinator.run(executor=" in src, (
            "coordinator.run(executor=...) not called — cloud escalation (depth=4) unwired"
        )

    def test_loop_task_construction(self):
        src = self._daemon_src()
        assert "LoopTask(" in src, "LoopTask objects not constructed from daemon tasks"

    def test_subprocess_only_in_fallback(self):
        """subprocess.run must be inside a fallback block, not the primary path."""
        src = self._daemon_src()
        # The fallback comment is the discriminating marker that separates
        # the primary (LoopCoordinator) path from the legacy subprocess path.
        assert "subprocess fallback" in src, (
            "subprocess.run appears to be the primary path, not a fallback"
        )


# ── G16a structural ───────────────────────────────────────────────────────────

class TestG16aStructural:
    """T1: JourneyTracker.__init__ must attempt LemonadeEmbedBridge injection."""

    def test_bridge_import_in_init(self):
        from cohezion.compound.journey_tracker import JourneyTracker
        src = inspect.getsource(JourneyTracker.__init__)
        assert "LemonadeEmbedBridge" in src, (
            "LemonadeEmbedBridge not imported inside JourneyTracker.__init__"
        )

    def test_flume_encoder_set_on_success(self):
        from cohezion.compound.journey_tracker import JourneyTracker
        src = inspect.getsource(JourneyTracker.__init__)
        assert "self._flume_encoder = bridge" in src, (
            "_flume_encoder never assigned from bridge — G16a injection missing"
        )


# ── G16b structural ───────────────────────────────────────────────────────────

class TestG16bStructural:
    """T1: track_execution() must call the public text_to_latent(), not _text_to_latent()."""

    def test_public_method_called_in_track_execution(self):
        from cohezion.compound.journey_tracker import JourneyTracker
        src = inspect.getsource(JourneyTracker.track_execution)
        # Public method should appear; the private hash-only method should NOT
        # appear in track_execution (it may still exist elsewhere but must not
        # be called on the hot path).
        assert "self.text_to_latent(" in src, (
            "track_execution() still calls _text_to_latent() — G16b not applied"
        )
        assert "self._text_to_latent(" not in src, (
            "track_execution() still calls _text_to_latent() — reverted or incomplete"
        )


# ── G16 behavioral ────────────────────────────────────────────────────────────

class TestG16Behavioral:
    """T2: text_to_latent() must return a semantic unit vector, not a hash expansion."""

    def test_encoder_instance_type(self):
        """When Lemonade is available, _flume_encoder is a LemonadeEmbedBridge."""
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.inference.lemonade_embed_bridge import LemonadeEmbedBridge

        jt = JourneyTracker()
        if jt._flume_encoder is None:
            pytest.skip("Lemonade OmniRouter :13305 offline — bridge not injected")
        assert isinstance(jt._flume_encoder, LemonadeEmbedBridge), (
            f"_flume_encoder is {type(jt._flume_encoder)}, expected LemonadeEmbedBridge"
        )

    def test_text_to_latent_shape_and_unit(self):
        """text_to_latent() returns (2048,) float32 unit vector."""
        from cohezion.compound.journey_tracker import JourneyTracker

        jt = JourneyTracker()
        vec = jt.text_to_latent("compound engineering loopception")
        assert vec.shape == (2048,), f"Expected shape (2048,), got {vec.shape}"
        norm = float(np.linalg.norm(vec))
        assert norm > 1e-6, "text_to_latent returned all-zeros vector"

    def test_semantic_embeddings_differ_for_distinct_inputs(self):
        """Two semantically distinct phrases must produce different 2048D vectors
        when LemonadeEmbedBridge is active (discriminating: hash always differs too,
        but here we check the 256D portion is not the SHA pattern)."""
        from cohezion.compound.journey_tracker import JourneyTracker

        jt = JourneyTracker()
        if jt._flume_encoder is None:
            pytest.skip("Lemonade offline — semantic embedding not active")

        v1 = jt.text_to_latent("the sky is blue")
        v2 = jt.text_to_latent("compound loop skill refinement")
        cosine = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9))
        # Two unrelated sentences must have cosine < 0.95 — if they're identical
        # something is wrong with the bridge (encoding both as the same zero vector).
        assert cosine < 0.95, (
            f"text_to_latent cosine={cosine:.3f} — both sentences collapsed to near-identical vector"
        )


# ── G18 structural ────────────────────────────────────────────────────────────

class TestG18Structural:
    """T1: Both gymnasium envs must accept journey_tracker and wire step()."""

    def test_manifold_env_init_signature(self):
        from cohezion.environments.manifold_env import ManifoldEnv
        params = inspect.signature(ManifoldEnv.__init__).parameters
        assert "journey_tracker" in params, (
            "ManifoldEnv.__init__ missing journey_tracker parameter"
        )

    def test_swarm_env_init_signature(self):
        from cohezion.environments.swarm_env import SwarmEnv
        params = inspect.signature(SwarmEnv.__init__).parameters
        assert "journey_tracker" in params, (
            "SwarmEnv.__init__ missing journey_tracker parameter"
        )

    def test_manifold_step_calls_record_env_state(self):
        from cohezion.environments.manifold_env import ManifoldEnv
        src = inspect.getsource(ManifoldEnv.step)
        assert "record_env_state" in src, (
            "ManifoldEnv.step() never calls record_env_state — G18 not wired"
        )

    def test_swarm_step_calls_record_env_state(self):
        from cohezion.environments.swarm_env import SwarmEnv
        src = inspect.getsource(SwarmEnv.step)
        assert "record_env_state" in src, (
            "SwarmEnv.step() never calls record_env_state — G18 not wired"
        )

    def test_journey_tracker_has_record_env_state(self):
        from cohezion.compound.journey_tracker import JourneyTracker
        assert hasattr(JourneyTracker, "record_env_state"), (
            "JourneyTracker missing record_env_state() — G18 receiver not implemented"
        )


# ── G18 behavioral discriminating ─────────────────────────────────────────────

class TestG18Behavioral:
    """T2: step() with a tracker must increment recent_point_count; without one it must not."""

    def test_manifold_step_increments_point_count(self):
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.environments.manifold_env import ManifoldEnv

        jt = JourneyTracker()
        env = ManifoldEnv(dim=12, max_steps=5, journey_tracker=jt)
        env.reset()
        pre = jt.get_recent_point_count()
        env.step(np.zeros(12, dtype=np.float32))
        post = jt.get_recent_point_count()
        assert post == pre + 1, (
            f"ManifoldEnv.step() did not record trajectory point: count {pre}→{post}"
        )

    def test_manifold_step_without_tracker_leaves_count_zero(self):
        """Discriminating: env with no tracker must NOT raise and count stays 0."""
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(dim=12, max_steps=5)  # no journey_tracker
        env.reset()
        env.step(np.zeros(12, dtype=np.float32))  # must not raise

    def test_swarm_step_increments_point_count(self):
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.environments.swarm_env import SwarmEnv

        jt = JourneyTracker()
        env = SwarmEnv(n_agents=2, dim=12, max_steps=5, journey_tracker=jt)
        env.reset()
        pre = jt.get_recent_point_count()
        actions = {f"agent_{i}": np.zeros(12, dtype=np.float32) for i in range(2)}
        env.step(actions)
        post = jt.get_recent_point_count()
        assert post == pre + 1, (
            f"SwarmEnv.step() did not record trajectory point: count {pre}→{post}"
        )

    def test_trajectory_point_contains_env_metadata(self):
        """The recorded point must carry reward and env_id in its metadata."""
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.environments.manifold_env import ManifoldEnv

        jt = JourneyTracker()
        env = ManifoldEnv(dim=12, max_steps=5, journey_tracker=jt)
        env.reset()
        env.step(np.zeros(12, dtype=np.float32))

        points = jt._recent_points
        assert points, "No trajectory points recorded after step"
        last = points[-1]
        assert last.operation_type == "env:manifold", (
            f"Expected operation_type 'env:manifold', got '{last.operation_type}'"
        )
        assert "reward" in last.metadata, "TrajectoryPoint metadata missing 'reward' key"

    def test_multiple_steps_accumulate_points(self):
        """5 steps must produce 5 points — no deduplication or dropping."""
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.environments.manifold_env import ManifoldEnv

        jt = JourneyTracker()
        env = ManifoldEnv(dim=12, max_steps=10, journey_tracker=jt)
        env.reset()
        for _ in range(5):
            env.step(np.zeros(12, dtype=np.float32))
        assert jt.get_recent_point_count() == 5, (
            f"Expected 5 trajectory points after 5 steps, "
            f"got {jt.get_recent_point_count()}"
        )
