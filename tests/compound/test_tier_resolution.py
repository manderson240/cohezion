"""V-model tests for the GIC routing-signal synthesis (_resolve_tier, 2026-06-29).

The executor computed three routing signals (DifficultyEstimator predicted_tier, DegradationDetector
suggested_tier, JepaGate verdict) but never combined them, and REROUTE was only logged. _resolve_tier
unifies them into one coherent recommendation and makes REROUTE actionable (downgrade toward cheaper).
"""
from __future__ import annotations

from cohezion.compound.executor import _TIER_ORDER, _resolve_tier


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
