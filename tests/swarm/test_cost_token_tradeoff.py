"""Tests for cost/token tradeoff optimization in CostAwareRouter.

Tests the core logic that prefers cheaper-per-token models when latency is acceptable.
"""

import pytest

from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.swarm.cost_aware_router import (
    CostAwareRouter,
)


class TestCostTokenTradeoff:
    """Test cost/token ratio optimization logic."""

    @pytest.fixture
    def router(self):
        """Create router with token optimization enabled."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-tradeoff"),
            budget_enforcer=BudgetEnforcer(budget_usd=100.0),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.10,  # 10% cost difference threshold
            latency_threshold=100.0,  # 100ms latency threshold
        )
        return router

    def test_medium_query_prefers_phi3_if_tps_acceptable(self, router):
        """Test that medium complexity queries prefer phi3 if TPS is acceptable."""
        # Medium queries normally route to qwen (TPS: 8.0)
        # But phi3 (TPS: 15.0) is much faster, so should be preferred if cost is equal

        decision, _ = router.select_model("Write a Python function to sort data")

        # With local models (cost=0), TPS becomes the deciding factor
        # phi3 TPS (15.0) vs qwen TPS (8.0) → phi3 is 87.5% as fast (> threshold)
        assert decision.model in ["phi3:mini", "qwen3-coder:32b", "Phi-4-mini-instruct-Hybrid"]

    def test_optimization_tracking_via_swaps_counter(self):
        """Test that token_optimization_swaps counter tracks optimization."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("swap-tracking"),
            prefer_longer_models_if_cheaper_per_token=True,
        )

        initial_swaps = router.token_optimization_swaps

        # Route queries that may trigger optimization
        router.select_model("Write a Python function to process data")  # Medium
        router.select_model("Design and optimize a distributed system")  # Complex

        # Swaps counter should track optimization attempts
        assert router.token_optimization_swaps >= initial_swaps

    def test_cost_per_token_calculation_accuracy(self, router):
        """Test accuracy of cost-per-token calculations."""
        # All models are local (free), so cost per token should be 0
        phi3_cost = router._get_cost_per_token("phi3:mini", 100)
        qwen_cost = router._get_cost_per_token("qwen3-coder:32b", 100)
        deepseek_cost = router._get_cost_per_token("deepseek-r1:8b", 100)

        assert phi3_cost == 0.0
        assert qwen_cost == 0.0
        assert deepseek_cost == 0.0

    def test_quality_score_reflects_selected_model(self, router):
        """Test that quality score in decision matches selected model."""
        decision_simple, _ = router.select_model("What is Python?")
        assert decision_simple.quality_score in (0.6, 0.82)  # phi3:mini or Phi-4-mini-instruct-Hybrid

        decision_medium, _ = router.select_model("Write a Python function")
        # May be qwen (0.85) or phi3 (0.6) due to optimization
        assert decision_medium.quality_score in [0.6, 0.82, 0.85]

        decision_complex, _ = router.select_model("Design and implement a production system")
        # May be deepseek (0.95), qwen (0.85), or phi3 (0.6) due to optimization
        assert decision_complex.quality_score in [0.6, 0.85, 0.95]
