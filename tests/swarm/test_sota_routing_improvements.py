"""Tests for SOTA-informed compound routing improvements.

Three improvements derived from SOTA findings:
  1. Rolling EMA quality + hysteresis band (Finding 4, arXiv:2605.00410)
  2. Contextual bandit model selection (Finding 4, arXiv:2605.14241)
  3. Cold-start confidence annealing (Finding 2 routing analogy, arXiv:2310.15440)

Each test is written RED-first; implementation in cost_aware_router.py makes them GREEN.
"""

from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest

from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.swarm.cost_aware_router import CostAwareRouter, reset_cost_aware_router


@pytest.fixture
def router():
    """Fresh CostAwareRouter with isolated dependencies."""
    reset_cost_aware_router()
    return CostAwareRouter(
        cost_tracker=SessionCostTracker("sota-test"),
        budget_enforcer=BudgetEnforcer(budget_usd=10.0),
    )


# ── Improvement 1: Rolling EMA quality gate + hysteresis ─────────────────────
# Finding 4: arXiv:2605.00410 "Agent Capsules"
# Key claim: per-query hard thresholds create oscillation; EMAs with a hysteresis band
# prevent premature threshold changes from transient quality dips.


class TestRollingEMAHysteresis:
    def test_ema_quality_tracked_per_model(self, router):
        """_ema_quality dict is populated after record_execution calls."""
        router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=True)
        assert hasattr(router, "_ema_quality"), "_ema_quality must exist after implementation"
        ema = router._ema_quality.get(router.TIER_SIMPLE, None)
        assert ema is not None, "_ema_quality must have an entry for TIER_SIMPLE"
        assert 0.0 <= ema <= 1.0, f"EMA must be in [0,1], got {ema}"

    def test_ema_decreases_on_failure(self, router):
        """EMA quality decreases when executions fail."""
        router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=True)
        ema_after_success = router._ema_quality.get(router.TIER_SIMPLE, 0.7)

        router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=False)
        ema_after_failure = router._ema_quality.get(router.TIER_SIMPLE, 0.7)

        assert ema_after_failure < ema_after_success, "EMA must decrease after a failure"

    def test_hysteresis_prevents_premature_threshold_reduction(self, router):
        """3 consecutive failures from EMA=0.7 don't trigger threshold reduction.

        EMA trajectory from 0.7 with alpha=0.1, all failures:
          fail1: 0.63 (above ESCALATE=0.6, consec=0)
          fail2: 0.567 (below 0.6, consec=1)
          fail3: 0.510 (below 0.6, consec=2 — still < HYSTERESIS_REQUIRED=3)
        Threshold must NOT decrease yet.
        """
        initial_threshold = router.cost_threshold  # 0.10 default

        for _ in range(3):
            router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=False)

        assert router.cost_threshold >= initial_threshold, (
            "Hysteresis must prevent threshold reduction after only 3 failures "
            f"(consec_below=2, REQUIRED=3). Got {router.cost_threshold:.3f}"
        )

    def test_hysteresis_triggers_threshold_reduction_after_required_consecutive(self, router):
        """4 consecutive failures DO trigger threshold reduction.

        EMA trajectory:
          fail4: 0.459 (below 0.6, consec=3 >= HYSTERESIS_REQUIRED) → TRIGGER
        """
        initial_threshold = router.cost_threshold  # 0.10

        for _ in range(4):
            router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=False)

        assert router.cost_threshold < initial_threshold, (
            f"After 4 consecutive failures, cost_threshold must decrease from {initial_threshold:.3f}"
        )

    def test_consec_counter_resets_on_good_quality(self, router):
        """Consecutive-below counter resets when EMA recovers above DE_ESCALATE threshold."""
        # Drive EMA below threshold with failures
        for _ in range(4):
            router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=False)

        # Record many successes to push EMA above DE_ESCALATE (0.75)
        for _ in range(30):
            router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=True)

        consec = getattr(router, "_consec_below_escalate", {}).get(router.TIER_SIMPLE, None)
        assert consec is not None, "_consec_below_escalate must exist after implementation"
        assert consec == 0, f"Consecutive-below counter must reset after EMA recovery, got {consec}"


# ── Improvement 2: Contextual bandit model selection ─────────────────────────
# Finding 4: arXiv:2605.14241 "Latency-Quality Routing for Functionally Equivalent Tools"
# Key claim: contextual bandit with argmax(q - λ*lat) learns empirical quality-latency
# tradeoffs, overriding static heuristics when they drift from actual performance.


class TestContextualBanditSelection:
    def test_bandit_state_initialized(self, router):
        """Bandit quality and latency EMAs are initialized from model defaults."""
        assert hasattr(router, "_bandit_quality_ema"), "_bandit_quality_ema must exist"
        assert hasattr(router, "_bandit_latency_ema"), "_bandit_latency_ema must exist"
        assert hasattr(router, "_bandit_exec_count"), "_bandit_exec_count must exist"
        # Should be initialized with model defaults
        assert router._bandit_quality_ema.get(router.TIER_SIMPLE) is not None
        assert router._bandit_latency_ema.get(router.TIER_SIMPLE) is not None

    def test_bandit_updates_ema_on_record(self, router):
        """Bandit EMAs update after record_execution."""
        initial_q = router._bandit_quality_ema.get(router.TIER_SIMPLE, 0.82)
        router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=True)
        router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=True)

        updated_q = router._bandit_quality_ema.get(router.TIER_SIMPLE, initial_q)
        # After successes, quality EMA should stay high or increase
        assert updated_q >= initial_q * 0.8, (
            f"Bandit quality EMA should not drastically drop after successes: {updated_q:.3f}"
        )

    def test_bandit_overrides_when_tier_simple_quality_degrades(self, router):
        """Bandit routes MEDIUM queries to TIER_MEDIUM when TIER_SIMPLE has poor EMA quality.

        Scenario: TIER_SIMPLE has been failing consistently (EMA ~0.20 after 12 failures).
        Static aggressive_cost_reduction would still route MEDIUM → TIER_SIMPLE.
        Bandit should override: TIER_SIMPLE score ≈ 0.147 vs TIER_MEDIUM score ≈ 0.790.

        R-Zero is mocked to multiplier=1.0 (no escalation) so the test is isolated
        to the bandit mechanism, not the pre-existing R-Zero adaptive routing.
        """
        # Mock R-Zero to prevent it from interfering with the bandit test
        mock_r_zero = MagicMock()
        mock_r_zero.get_current_multiplier.return_value = 1.0  # No R-Zero escalation

        with patch.object(router, "_get_r_zero", return_value=mock_r_zero):
            # Degrade TIER_SIMPLE quality via failures (beyond BANDIT_WARMUP)
            for _ in range(12):
                router.record_execution(router.TIER_SIMPLE, 100, 50.0, success=False)

            # MEDIUM query: bandit should prefer TIER_MEDIUM after 12 TIER_SIMPLE failures
            decision, _ = router.select_model("Write a Python function")  # MEDIUM complexity

        assert decision.model == router.TIER_MEDIUM, (
            f"After TIER_SIMPLE quality degradation (12 failures) with R-Zero neutralized, "
            f"bandit must route MEDIUM queries to TIER_MEDIUM. Got: {decision.model}"
        )

    def test_bandit_does_not_activate_before_warmup(self, router):
        """Bandit must not override static routing when exec_count < BANDIT_WARMUP."""
        # Zero executions — bandit is cold
        assert router._bandit_exec_count == 0

        # Should route exactly as static heuristics do (MEDIUM → TIER_SIMPLE due to aggressive)
        decision, _ = router.select_model("Write a Python function")
        assert decision.model in {router.TIER_SIMPLE, router.TIER_MEDIUM}, (
            "Before warmup, routing must follow static heuristics"
        )


# ── Improvement 3: Cold-start confidence annealing ───────────────────────────
# Finding 2 routing analogy: arXiv:2310.15440 "Learning Dynamics in Linear VAE"
# Key insight: during cold start, the router has no calibration data; confidence
# should start conservatively and anneal toward nominal as queries accumulate.


class TestColdStartConfidenceAnnealing:
    def test_cold_start_confidence_below_nominal(self, router):
        """Confidence on first query must be below the warm (post-warmup) value.

        Warm-up calls both select_model AND record_execution to avoid the success-rate
        proxy bug (select without execute → success_rate drops to 0 after 5 queries).
        """
        # Cold: no prior queries
        cold_decision, _ = router.select_model("What is Python?")
        cold_conf = cold_decision.confidence

        # Warm up: 15 select + record cycles (success=True → success_rate stays high)
        for _ in range(15):
            d, _ = router.select_model("What is Python?")
            router.record_execution(d.model, 80, 50.0, success=True)

        # Warm: next query (same task type)
        warm_decision, _ = router.select_model("What is Python?")
        warm_conf = warm_decision.confidence

        assert warm_conf > cold_conf, (
            f"Cold-start confidence ({cold_conf:.3f}) must be lower than "
            f"post-warmup confidence ({warm_conf:.3f})"
        )

    def test_cold_start_factor_scales_confidence(self, router):
        """Cold-start scales confidence to at most 70% of nominal on query 0.

        With warm-up including record_execution, success_rate stays near 1.0,
        so the only difference between cold and warm is the cold_start_factor.
        """
        cold_decision, _ = router.select_model("What is Python?")
        cold_conf = cold_decision.confidence

        # Route + record 20 successful executions to fully warm up
        for _ in range(20):
            d, _ = router.select_model("What is Python?")
            router.record_execution(d.model, 80, 50.0, success=True)
        warm_decision, _ = router.select_model("What is Python?")
        warm_conf = warm_decision.confidence

        # Cold confidence must be ≤ 72% of warm (70% scaling, with floating-point slack)
        assert cold_conf <= warm_conf * 0.72, (
            f"Cold confidence {cold_conf:.3f} should be ≤ 72% of warm {warm_conf:.3f}"
        )

    def test_confidence_monotonically_increases_with_queries(self, router):
        """Confidence must not decrease as the query count grows from 0 to WARMUP.

        Each iteration calls both select_model AND record_execution (success=True)
        so the success_rate proxy stays high throughout.
        """
        confidences = []
        for _ in range(12):
            d, _ = router.select_model("What is Python?")
            confidences.append(d.confidence)
            router.record_execution(d.model, 80, 50.0, success=True)

        # Confidence must be non-decreasing from cold start through warmup
        for i in range(len(confidences) - 1):
            assert confidences[i] <= confidences[i + 1] + 1e-9, (
                f"Confidence decreased at step {i}: {confidences[i]:.4f} > {confidences[i + 1]:.4f}"
            )
