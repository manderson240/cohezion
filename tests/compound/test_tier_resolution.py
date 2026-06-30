"""V-model tests for the GIC routing-signal synthesis (_resolve_tier, 2026-06-29).

The executor computed three routing signals (DifficultyEstimator predicted_tier, DegradationDetector
suggested_tier, JepaGate verdict) but never combined them, and REROUTE was only logged. _resolve_tier
unifies them into one coherent recommendation and makes REROUTE actionable (downgrade toward cheaper).
"""
from __future__ import annotations

from cohezion.compound.executor import _call_execute_fn, _TIER_ORDER, _resolve_tier


class TestResolveTierStructural:
    def test_tier_order_cheapest_first(self):
        assert _TIER_ORDER == ("npu", "igpu", "cpu", "cloud")


class TestResolveTierBehavioral:
    def test_conservative_of_two_signals(self):
        # takes the cheaper (lower-index) of predicted vs suggested
        assert _resolve_tier("cpu", "npu", jepa_reroute=False) == "npu"
        assert _resolve_tier("igpu", "cloud", jepa_reroute=False) == "igpu"

    def test_reroute_downgrades_one_step_toward_cheaper(self):
        """Discriminating: REROUTE must CHANGE the recommendation toward a cheaper tier. A wrong
        impl that ignores the verdict (the old 'only logged' behavior) returns the base unchanged."""
        assert _resolve_tier("cpu", "cpu", jepa_reroute=False) == "cpu"  # baseline
        assert _resolve_tier("cpu", "cpu", jepa_reroute=True) == "igpu"  # REROUTE downgrades cpu→igpu

    def test_reroute_clamped_at_cheapest_tier(self):
        assert _resolve_tier("npu", "npu", jepa_reroute=True) == "npu"  # can't go below npu

    def test_no_valid_signal_returns_none(self):
        assert _resolve_tier(None, None, jepa_reroute=False) is None
        assert _resolve_tier(None, None, jepa_reroute=True) is None  # nothing to downgrade
        assert _resolve_tier("unknown", "bogus", jepa_reroute=False) is None

    def test_invalid_tier_ignored_valid_one_used(self):
        assert _resolve_tier("bogus", "cpu", jepa_reroute=False) == "cpu"


class TestCallExecuteFnBinding:
    """O9 binding: a confident high difficulty prediction enters the cascade above the cheap tiers,
    signature-aware + backward-compatible + conservative."""

    def test_confident_high_prediction_binds_min_tier_index(self):
        """Discriminating: predicted_tier='cpu' → execute_fn called with min_tier_index=2. A wrong
        impl that ignores the prediction calls with the default 0."""
        seen = {}

        def ex(guidance, min_tier_index=0):
            seen["idx"] = min_tier_index
            return "out", {}

        _call_execute_fn(ex, "g", "cpu")
        assert seen["idx"] == 2  # cpu → index 2

    def test_npu_unknown_none_do_not_skip(self):
        seen = {}

        def ex(guidance, min_tier_index=0):
            seen["idx"] = min_tier_index
            return "out", {}

        for pred in ("npu", "unknown", None):
            _call_execute_fn(ex, "g", pred)
            assert seen["idx"] == 0  # cheap-first default — no skip on low/unknown

    def test_one_arg_execute_fn_backward_compatible(self):
        """A legacy 1-arg execute_fn (no min_tier_index) is called with just guidance even on a high
        prediction — no TypeError, no crash."""
        calls = []

        def ex(guidance):  # no min_tier_index kwarg
            calls.append(guidance)
            return "out", {}

        out, _ = _call_execute_fn(ex, "g", "cpu")  # would be idx=2, but fn can't accept it
        assert out == "out" and calls == ["g"]


class TestCompactionReroute:
    """Fusion free-reroute at the compaction boundary — re-decide the tier where the cache rebuilds
    anyway, rerouting to the MORE-CAPABLE of (difficulty prediction, health suggestion)."""

    def _executor(self, suggested_tier):
        from unittest.mock import MagicMock

        from cohezion.compound.executor import CompoundExecutor
        from cohezion.compound.skill_refiner import SkillRefiner

        dd = MagicMock()
        dd.suggest_routing_tier.return_value = suggested_tier
        sr = SkillRefiner()
        for _ in range(4):  # teach: 'reason' needs cpu; 'greet' fine on npu
            sr._difficulty_estimator.record("reason", "op", "cpu", 2, 0.9)
            sr._difficulty_estimator.record("greet", "op", "npu", 0, 0.9)
        return CompoundExecutor(MagicMock(), degradation_detector=dd, skill_refiner=sr)

    def test_reroutes_hard_skill_up_at_compaction(self):
        """Discriminating: a hard skill (learned→cpu) on an active NPU tier reroutes to cpu. A
        no-reroute impl stays npu; a cheaper-bias impl would pick npu."""
        ex = self._executor(suggested_tier="npu")  # health fine
        assert ex._recompute_tier_at_compaction("reason", "op", active_tier="npu") == "cpu"

    def test_stays_when_already_adequate(self):
        ex = self._executor(suggested_tier="npu")
        assert ex._recompute_tier_at_compaction("reason", "op", active_tier="cpu") is None
        assert ex._recompute_tier_at_compaction("greet", "op", active_tier="npu") is None

    def test_health_degradation_escalates_even_easy_skill(self):
        ex = self._executor(suggested_tier="cpu")  # degraded health
        assert ex._recompute_tier_at_compaction("greet", "op", active_tier="npu") == "cpu"
