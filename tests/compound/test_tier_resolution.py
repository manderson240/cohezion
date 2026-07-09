"""V-model tests for the GIC routing-signal synthesis (_resolve_tier, 2026-06-29).

The executor computed three routing signals (DifficultyEstimator predicted_tier, DegradationDetector
suggested_tier, JepaGate verdict) but never combined them, and REROUTE was only logged. _resolve_tier
unifies them into one coherent recommendation and makes REROUTE actionable (downgrade toward cheaper).
"""

from __future__ import annotations

from cohezion.compound.executor import _TIER_ORDER, _call_execute_fn, _resolve_tier


class TestResolveTierStructural:
    def test_tier_order_cheapest_first(self):
        assert _TIER_ORDER == ("npu", "igpu", "cpu", "cloud")


class TestResolveTierBehavioral:
    def test_max_capability_of_two_signals(self):
        # H4: takes the MORE-CAPABLE (higher-index) of predicted vs suggested — health may only
        # escalate a predicted-hard task, never cheapen it (SLO/capability floor).
        assert _resolve_tier("cpu", "npu", jepa_reroute=False) == "cpu"
        assert _resolve_tier("igpu", "cloud", jepa_reroute=False) == "cloud"
        assert _resolve_tier("npu", "igpu", jepa_reroute=False) == "igpu"

    def test_reroute_escalates_one_step_toward_capability(self):
        """H4 discriminating: REROUTE (marginal coherence → expect divergence) escalates UP one tier.
        A wrong impl that ignores the verdict returns the base; the OLD cheaper-downgrade impl
        returns npu — both fail."""
        assert _resolve_tier("npu", "npu", jepa_reroute=False) == "npu"  # baseline
        assert (
            _resolve_tier("npu", "npu", jepa_reroute=True) == "igpu"
        )  # REROUTE escalates npu→igpu
        assert _resolve_tier("igpu", "igpu", jepa_reroute=True) == "cpu"

    def test_reroute_clamped_at_most_capable_tier(self):
        assert (
            _resolve_tier("cloud", "cloud", jepa_reroute=True) == "cloud"
        )  # can't escalate past cloud

    def test_no_valid_signal_returns_none(self):
        assert _resolve_tier(None, None, jepa_reroute=False) is None
        assert _resolve_tier(None, None, jepa_reroute=True) is None  # nothing to escalate
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


class TestOracleTierSignal:
    """OC1-OC3: CompoundHealthOracle regime-driven tier as 4th MAX-CAPABILITY routing signal.

    The oracle's _last_assessment.tier_recommendation reflects the rolling Higuchi-FD window
    (cross-session persistent).  STUCK regime (FD < 1.3) escalates tier to break over-exploitation;
    CHAOTIC regime forces cpu.  It participates in MAX-CAPABILITY fusion alongside predicted,
    suggested, and REROUTE — it can only raise the floor, never lower it.
    """

    def test_oc1_oracle_tier_parameter_in_signature(self):
        """OC1 structural: _resolve_tier accepts oracle_tier kwarg. A wrong impl (3-arg only)
        raises TypeError here."""
        import inspect

        params = inspect.signature(_resolve_tier).parameters
        assert "oracle_tier" in params, "oracle_tier missing from _resolve_tier signature"

    def test_oc2_oracle_stuck_escalates_npu_to_igpu(self):
        """OC2 discriminating: oracle STUCK regime → oracle_tier='igpu'; predicted='npu'; suggested=None.
        Correct impl returns 'igpu'.  Wrong impl ignoring oracle_tier returns 'npu'."""
        result = _resolve_tier(
            predicted="npu",
            suggested=None,
            jepa_reroute=False,
            oracle_tier="igpu",  # STUCK regime escalated from npu
        )
        assert result == "igpu", f"Expected 'igpu' (oracle STUCK floor), got {result!r}"

    def test_oc3_oracle_chaotic_forces_cpu(self):
        """OC3 discriminating: CHAOTIC regime sets oracle_tier='cpu'; even easy skill on npu gets
        escalated.  Wrong impl ignoring oracle_tier returns 'npu'."""
        result = _resolve_tier(
            predicted="npu",
            suggested="npu",
            jepa_reroute=False,
            oracle_tier="cpu",  # CHAOTIC → maximum reasoning depth
        )
        assert result == "cpu", f"Expected 'cpu' (oracle CHAOTIC floor), got {result!r}"

    def test_oc4_oracle_hiho_does_not_downgrade_confident_cpu_prediction(self):
        """OC4 correctness: HIHO oracle_tier='npu' does NOT lower a confident cpu prediction.
        MAX-CAPABILITY picks the more-capable signal — oracle only raises the floor, never lowers it."""
        result = _resolve_tier(
            predicted="cpu",
            suggested=None,
            jepa_reroute=False,
            oracle_tier="npu",  # HIHO healthy — would prefer npu
        )
        assert result == "cpu", f"Expected 'cpu' (predicted dominates), got {result!r}"

    def test_oc5_oracle_tier_none_backward_compatible(self):
        """OC5: default oracle_tier=None preserves existing 3-signal behavior — existing callers
        passing 3 positional args are unaffected (backward-compatible signature extension)."""
        assert _resolve_tier("npu", "igpu", jepa_reroute=False) == "igpu"
        assert _resolve_tier("cpu", "npu", jepa_reroute=False) == "cpu"
        assert _resolve_tier(None, None, jepa_reroute=False) is None
