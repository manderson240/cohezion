"""V-model tests for MoESkillRouter (#83).

T1 (structural) → T2 (discriminating behavioral).
Harness entries: MR1–MR4.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from cohezion.compound.moe_skill_router import MoESkillRouter  # type: ignore[reportMissingImports]
from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner


# ── T1: Structural ───────────────────────────────────────────────────────────


class TestMR1Structure:
    def test_expert_names_match_autodata_perspectives(self):
        """MR1: Router expert names align with _AUTODATA_PERSPECTIVES keys."""
        router = MoESkillRouter()
        assert set(router._EXPERT_NAMES) == {"quality", "efficiency", "caching", "tier", "fallback"}

    def test_weights_initialized_uniformly(self):
        """MR1: Each expert starts with equal weight."""
        router = MoESkillRouter()
        n = len(router._EXPERT_NAMES)
        expected = 1.0 / n
        for name in router._EXPERT_NAMES:
            assert abs(router.get_weight(name) - expected) < 1e-9

    def test_route_returns_expert_name(self):
        """MR3: route() always returns a valid expert name."""
        router = MoESkillRouter()
        result = router.route("my_skill", MagicMock())
        assert result in router._EXPERT_NAMES

    def test_skill_refiner_accepts_moe_router_kwarg(self):
        """MR4: SkillRefiner.__init__ has moe_router parameter."""
        params = inspect.signature(SkillRefiner.__init__).parameters
        assert "moe_router" in params

    def test_moe_router_stored_on_skill_refiner(self):
        """MR4: SkillRefiner stores moe_router when provided."""
        router = MoESkillRouter()
        sr = SkillRefiner(moe_router=router)
        assert sr._moe_router is router

    def test_skill_refiner_none_moe_router_by_default(self):
        """MR4: SkillRefiner._moe_router is None when not provided."""
        sr = SkillRefiner()
        assert sr._moe_router is None


# ── T2: Discriminating Behavioral ────────────────────────────────────────────


class TestMR2WeightLearning:
    def test_update_increases_expert_weight(self):
        """Positive quality delta raises the targeted expert weight."""
        router = MoESkillRouter(alpha=0.5)
        initial = router.get_weight("quality")
        router.update("quality", +1.0)
        assert router.get_weight("quality") > initial

    def test_update_decreases_expert_weight_on_negative_delta(self):
        """Negative quality delta lowers the targeted expert weight."""
        router = MoESkillRouter(alpha=0.5)
        initial = router.get_weight("quality")
        router.update("quality", -1.0)
        assert router.get_weight("quality") < initial

    def test_update_unknown_expert_is_noop(self):
        """update() with an unknown expert name doesn't crash or mutate weights."""
        router = MoESkillRouter()
        snapshot = dict(router.weights)
        router.update("nonexistent", 1.0)
        assert router.weights == snapshot

    def test_replay_batch_shifts_weights(self):
        """replay() with repeated quality expert wins makes quality the top expert."""
        router = MoESkillRouter(alpha=0.3)
        history = [("quality", 1.0)] * 20
        router.replay(history)
        best = max(router.weights, key=lambda k: router.weights[k])
        assert best == "quality"

    def test_replay_empty_history_is_noop(self):
        """replay() with empty list leaves weights unchanged."""
        router = MoESkillRouter()
        snapshot = dict(router.weights)
        router.replay([])
        assert router.weights == snapshot

    def test_route_returns_highest_weight_expert(self):
        """route() returns the expert with the highest current weight."""
        router = MoESkillRouter(alpha=0.9)
        # Make tier the dominant expert
        router.update("tier", 1.0)
        router.update("tier", 1.0)
        result = router.route("any_skill", MagicMock())
        assert result == "tier"


class TestMR4SkillRefinerIntegration:
    def _metrics(self, **kwargs) -> ExecutionMetrics:
        defaults = dict(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=100.0,
            quality_score=0.5,
            anomaly_score=0.1,
            cached_hits=0,
        )
        defaults.update(kwargs)
        return ExecutionMetrics(**defaults)  # type: ignore[arg-type]

    def test_generate_recommendation_runs_with_router(self):
        """_generate_recommendation() doesn't crash when moe_router is wired."""
        router = MoESkillRouter()
        sr = SkillRefiner(moe_router=router)
        result = sr._generate_recommendation(self._metrics(), "test_op")
        assert isinstance(result, str) and len(result) > 0

    def test_moe_router_biases_toward_dominant_expert(self):
        """When caching expert is dominant, caching-themed candidate is more likely selected."""
        router = MoESkillRouter(alpha=0.9)
        # Drive up caching weight drastically
        for _ in range(30):
            router.update("caching", 1.0)

        sr = SkillRefiner(moe_router=router)
        m = self._metrics(cached_hits=5)  # cache condition active
        results = [sr._generate_recommendation(m, "read") for _ in range(10)]
        # At least some results should mention caching/cache
        caching_hits = sum(1 for r in results if "cache" in r.lower())
        assert caching_hits >= 5, f"Expected caching bias, got: {results}"
