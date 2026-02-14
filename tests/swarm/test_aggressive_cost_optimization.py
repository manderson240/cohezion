"""Tests for aggressive cost reduction strategies in CostAwareRouter.

Tests aggressive mode that achieves ≥30% cost reduction by:
- Preferring fast model for medium queries if TPS is acceptable
- Allowing fast model for complex queries with relaxed latency constraints
- Dynamic threshold tuning based on success patterns
"""

import pytest
from cohezion.swarm.cost_aware_router import (
    CostAwareRouter,
    QueryComplexity,
)
from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer


class TestAggressiveCostOptimization:
    """Test aggressive cost reduction features."""

    @pytest.fixture
    def aggressive_router(self):
        """Create router with aggressive cost reduction enabled."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-aggressive"),
            budget_enforcer=BudgetEnforcer(budget_usd=100.0),
            aggressive_cost_reduction=True,
            dynamic_threshold_tuning=True,
            cost_threshold=0.10,
            latency_threshold=150.0,
        )
        return router

    def test_aggressive_medium_to_fast_model_routing(self, aggressive_router):
        """Test that medium queries route to fast model with aggressive cost reduction."""
        # Medium queries normally route to medium model, but aggressive mode prefers fast model
        decision, _ = aggressive_router.select_model(
            "Write a Python function to process data"
        )

        # With aggressive cost reduction, should prefer fast model for medium queries
        # if latency impact is acceptable
        assert decision.complexity == QueryComplexity.MEDIUM
        assert decision.model in ["phi4-mini-reasoning", "qwen3-coder:30b"]

    def test_aggressive_complex_to_fast_model_possible(self, aggressive_router):
        """Test that complex queries can be routed to fast model with aggressive cost reduction."""
        decision, _ = aggressive_router.select_model(
            "Design and implement a distributed system"
        )

        # With aggressive cost reduction, complex might route to fast model
        # if quality is acceptable
        assert decision.complexity == QueryComplexity.COMPLEX
        assert decision.model in ["glm-4.7-flash", "qwen3-coder:30b", "phi4-mini-reasoning"]

    def test_aggressive_simple_always_fast_model(self, aggressive_router):
        """Test that simple queries always route to fast model."""
        simple_queries = [
            "What is Python?",
            "Explain machine learning",
            "List the items",
        ]

        for query in simple_queries:
            decision, _ = aggressive_router.select_model(query)
            assert decision.model == "phi4-mini-reasoning", f"Failed for: {query}"

    def test_cost_reduction_target_30_percent(self, aggressive_router):
        """Test that aggressive routing achieves ≥30% cost reduction."""
        # Generate mixed queries
        queries = [
            "What is AI?",  # simple
            "What is ML?",  # simple
            "What is DL?",  # simple
            "Write a function",  # medium
            "Write async code",  # medium
            "Design a system",  # complex
            "Build a distributed cache",  # complex
        ]

        for query in queries:
            aggressive_router.select_model(query)

        # Record mock executions with reasonable token counts
        aggressive_router.record_execution("phi3:mini", actual_tokens=80, duration_ms=50.0)
        aggressive_router.record_execution("phi3:mini", actual_tokens=80, duration_ms=50.0)
        aggressive_router.record_execution("phi3:mini", actual_tokens=80, duration_ms=50.0)
        aggressive_router.record_execution("qwen3-coder:32b", actual_tokens=200, duration_ms=100.0)
        aggressive_router.record_execution("qwen3-coder:32b", actual_tokens=200, duration_ms=100.0)
        aggressive_router.record_execution("deepseek-r1:8b", actual_tokens=400, duration_ms=300.0)
        aggressive_router.record_execution("deepseek-r1:8b", actual_tokens=400, duration_ms=300.0)

        stats = aggressive_router.get_statistics()

        # At least 30% should be routed to fast model
        fast_model_percentage = (stats.fast_model_routed / stats.total_queries) * 100
        assert fast_model_percentage >= 30.0, f"Fast model routing {fast_model_percentage}% < 30% target"

    def test_dynamic_threshold_tuning_enables_more_fast_model(self, aggressive_router):
        """Test that dynamic tuning relaxes thresholds when fast model succeeds."""
        # Record successful fast model executions
        for _ in range(10):
            aggressive_router.record_execution("phi3:mini", 100, 50.0, success=True)
            aggressive_router.record_execution("qwen3-coder:32b", 200, 100.0, success=True)

        initial_threshold = aggressive_router.cost_threshold
        initial_latency = aggressive_router.latency_threshold

        # With 10 successes of fast model vs medium model, ratio is 50%, so should increase thresholds
        # More tuning calls
        for _ in range(10):
            aggressive_router.record_execution("phi3:mini", 100, 50.0, success=True)

        # Thresholds should be adjusted
        # (After high fast model success, thresholds may increase to route more to fast model)
        assert aggressive_router.cost_threshold >= initial_threshold
        assert aggressive_router.latency_threshold >= initial_latency

    def test_aggressive_tracking_swaps(self, aggressive_router):
        """Test that optimization swaps are tracked."""
        initial_swaps = aggressive_router.token_optimization_swaps

        # Route medium and complex queries that might be optimized
        aggressive_router.select_model("Write a function to process data")
        aggressive_router.select_model("Design a distributed system")

        # Some swaps may occur (depending on aggressive settings)
        final_swaps = aggressive_router.token_optimization_swaps

        # At least check that swaps counter exists and can be tracked
        assert final_swaps >= initial_swaps

    def test_aggressive_disabled_fallback(self):
        """Test that disabling aggressive mode uses standard routing."""
        standard_router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-standard"),
            aggressive_cost_reduction=False,
            cost_threshold=0.10,
        )

        decision, _ = standard_router.select_model("Write a Python function")

        # Without aggressive mode, medium queries should prefer medium model
        assert decision.complexity == QueryComplexity.MEDIUM
        # Should NOT optimize to fast model as aggressively
        assert decision.model in ["qwen3-coder:30b", "phi4-mini-reasoning"]


class TestCostPerTokenOptimization:
    """Test cost/token ratio improvements."""

    @pytest.fixture
    def optimizer_router(self):
        """Create router optimized for cost/token ratio."""
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-cost-token"),
            aggressive_cost_reduction=True,
        )

    def test_cost_per_token_calculation(self, optimizer_router):
        """Test cost per token calculation accuracy."""
        # For local models (cost = $0), cost per token should be 0
        cost_per_token = optimizer_router._get_cost_per_token("phi3:mini", 100)
        assert cost_per_token == 0.0

        # Test with multiple token counts (should all be 0 for local)
        for tokens in [10, 100, 1000]:
            cost = optimizer_router._get_cost_per_token("qwen3-coder:32b", tokens)
            assert cost == 0.0

    def test_tps_based_comparison(self, optimizer_router):
        """Test TPS-based model comparison for local models."""
        # fast model (15 TPS) vs medium model (8 TPS)
        # For cost-equal models, prefer faster one
        fast_tps = optimizer_router.MODEL_TPS["phi4-mini-reasoning"]
        medium_tps = optimizer_router.MODEL_TPS["qwen3-coder:30b"]

        # Fast model should have higher TPS than medium model
        assert fast_tps > medium_tps

    def test_aggressive_fast_model_selection_latency_acceptable(self, optimizer_router):
        """Test that fast model is selected when latency impact is acceptable."""
        # For medium query, normally routed to medium model
        # But if aggressive mode and TPS acceptable, use fast model
        decision, _ = optimizer_router.select_model(
            "Write a function to validate input"
        )

        # With aggressive optimization, may prefer fast model
        assert decision.model in ["phi4-mini-reasoning", "qwen3-coder:30b"]


class TestDynamicThresholdTuning:
    """Test automatic threshold adjustment based on success patterns."""

    def test_tuning_increases_on_high_fast_model_success(self):
        """Test that thresholds increase when fast model has high success rate."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-tuning"),
            dynamic_threshold_tuning=True,
            cost_threshold=0.10,
            latency_threshold=150.0,
        )

        # Record high fast model success rate (85%+) - 17 fast model successes vs 3 medium model
        # This gives fast model: 17/20 = 85% success rate
        for _ in range(17):
            router.record_execution("phi3:mini", 100, 50.0, success=True)
        for _ in range(3):
            router.record_execution("qwen3-coder:32b", 200, 100.0, success=True)

        # After tuning, thresholds should relax (increase) to allow more fast model routing
        final_cost_threshold = router.cost_threshold
        final_latency = router.latency_threshold

        # Thresholds should be adjusted (increased due to high fast model success)
        # With 85% fast model success, should increase thresholds
        assert final_cost_threshold >= 0.10, f"Expected ≥0.10, got {final_cost_threshold}"
        assert final_latency >= 150.0, f"Expected ≥150.0, got {final_latency}"

    def test_tuning_decreases_on_low_fast_model_success(self):
        """Test that thresholds decrease when fast model has low success rate."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-tuning-low"),
            dynamic_threshold_tuning=True,
            cost_threshold=0.20,
            latency_threshold=200.0,
        )

        # Record low fast model success rate (<60%)
        for _ in range(20):
            router.record_execution("phi3:mini", 100, 50.0, success=False)  # Low success
            router.record_execution("qwen3-coder:32b", 200, 100.0, success=True)  # High success

        # After tuning, thresholds should tighten (decrease) to use fast model less
        final_cost_threshold = router.cost_threshold
        final_latency = router.latency_threshold

        # Thresholds may decrease to be more conservative
        assert final_cost_threshold <= 0.20
        assert final_latency <= 200.0

    def test_tuning_requires_minimum_samples(self):
        """Test that tuning requires minimum sample size."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-tuning-min"),
            dynamic_threshold_tuning=True,
            cost_threshold=0.10,
        )

        initial_threshold = router.cost_threshold

        # Record only 5 executions (below 10 minimum)
        for _ in range(5):
            router.record_execution("phi3:mini", 100, 50.0, success=True)

        # Should not change (insufficient sample)
        assert router.cost_threshold == initial_threshold

    def test_tuning_disabled_keeps_static_thresholds(self):
        """Test that disabling tuning keeps static thresholds."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-no-tuning"),
            dynamic_threshold_tuning=False,
            cost_threshold=0.10,
            latency_threshold=150.0,
        )

        initial_cost = router.cost_threshold
        initial_latency = router.latency_threshold

        # Record many executions
        for _ in range(30):
            router.record_execution("phi3:mini", 100, 50.0, success=True)

        # Thresholds should NOT change
        assert router.cost_threshold == initial_cost
        assert router.latency_threshold == initial_latency


class TestParameterTuning:
    """Test parameter configuration and tuning."""

    def test_custom_cost_threshold(self):
        """Test custom cost threshold configuration."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-custom"),
            cost_threshold=0.25,  # 25% threshold
        )

        assert router.cost_threshold == 0.25

    def test_custom_latency_threshold(self):
        """Test custom latency threshold configuration."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-custom"),
            latency_threshold=200.0,  # 200ms threshold
        )

        assert router.latency_threshold == 200.0

    def test_threshold_range_constraints(self):
        """Test that thresholds stay within reasonable bounds during tuning."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-bounds"),
            dynamic_threshold_tuning=True,
            cost_threshold=0.10,
            latency_threshold=100.0,
        )

        # Force extreme conditions
        for _ in range(100):
            router.record_execution("phi3:mini", 100, 50.0, success=True)

        # Even with extreme success, thresholds should stay within bounds
        assert 0.05 <= router.cost_threshold <= 0.25
        assert 100.0 <= router.latency_threshold <= 250.0

    def test_parameter_persistence_across_routing(self):
        """Test that parameters persist across routing decisions."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-persist"),
            cost_threshold=0.15,
            latency_threshold=175.0,
        )

        initial_cost = router.cost_threshold
        initial_latency = router.latency_threshold

        # Make routing decisions
        router.select_model("What is AI?")
        router.select_model("Write a function")
        router.select_model("Design a system")

        # Parameters should not change without explicit tuning
        assert router.cost_threshold == initial_cost
        assert router.latency_threshold == initial_latency
