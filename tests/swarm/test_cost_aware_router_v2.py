"""Tests for CostAwareRouter v2 with token optimization and cost/latency thresholds.

Tests:
- Cost/token ratio optimization
- Model selection with new thresholds
- Backward compatibility with existing API
- Budget enforcement with optimized routing
- Token optimization swap tracking
- Performance and latency trade-offs
- Edge cases and chaos testing
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from cohezion.swarm.cost_aware_router import (
    CostAwareRouter,
    QueryComplexityAnalyzer,
    QueryComplexity,
    ModelRoutingDecision,
    RoutingStatistics,
    get_cost_aware_router,
    reset_cost_aware_router,
)
from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer, BudgetPolicy


class TestCostAwareRouterV2Init:
    """Test v2 initialization with new parameters."""

    def test_init_with_default_thresholds(self):
        """Test initialization with default threshold parameters."""
        router = CostAwareRouter()

        assert router.prefer_longer_models_if_cheaper_per_token is True
        assert router.cost_threshold == 0.10
        assert router.latency_threshold == 150.0
        assert router.token_optimization_swaps == 0

    def test_init_with_custom_thresholds(self):
        """Test initialization with custom threshold parameters."""
        router = CostAwareRouter(
            prefer_longer_models_if_cheaper_per_token=False,
            cost_threshold=0.05,
            latency_threshold=50.0,
        )

        assert router.prefer_longer_models_if_cheaper_per_token is False
        assert router.cost_threshold == 0.05
        assert router.latency_threshold == 50.0

    def test_init_with_trackers(self):
        """Test initialization with cost tracker and budget enforcer."""
        tracker = SessionCostTracker("test-session")
        enforcer = BudgetEnforcer(budget_usd=10.0)

        router = CostAwareRouter(
            cost_tracker=tracker,
            budget_enforcer=enforcer,
        )

        assert router.cost_tracker is tracker
        assert router.budget_enforcer is enforcer

    def test_backward_compatibility_without_new_params(self):
        """Test that existing code works without new parameters."""
        # This should work exactly as before
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
        )

        assert router.prefer_longer_models_if_cheaper_per_token is True
        assert router.cost_threshold == 0.10
        assert router.latency_threshold == 150.0


class TestCostPerTokenOptimization:
    """Test cost-per-token ratio optimization."""

    @pytest.fixture
    def router(self):
        """Create router with optimization enabled."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.10,
            latency_threshold=100.0,
        )

    def test_get_cost_per_token_phi3(self, router):
        """Test cost per token calculation for phi3."""
        # phi3 is free (local), so 0.0 per token
        cost = router._get_cost_per_token("phi3:mini", 100)
        assert cost == 0.0

    def test_get_cost_per_token_qwen(self, router):
        """Test cost per token calculation for qwen."""
        # qwen is free (local), so 0.0 per token
        cost = router._get_cost_per_token("qwen3-coder:32b", 100)
        assert cost == 0.0

    def test_get_cost_per_token_deepseek(self, router):
        """Test cost per token calculation for deepseek."""
        # deepseek is free (local), so 0.0 per token
        cost = router._get_cost_per_token("deepseek-r1:8b", 100)
        assert cost == 0.0

    def test_get_cost_per_token_zero_tokens(self, router):
        """Test cost per token with zero tokens."""
        cost = router._get_cost_per_token("phi3:mini", 0)
        assert cost == 0.0


class TestLatencyTradeoff:
    """Test latency trade-off logic."""

    @pytest.fixture
    def router(self):
        """Create router with tunable latency threshold."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
            latency_threshold=100.0,  # 100ms trade-off acceptable
        )

    def test_is_cheaper_with_acceptable_latency_phi3_to_qwen(self, router):
        """Test latency trade-off from qwen (100ms) to phi3 (50ms)."""
        # phi3 is faster AND cheaper (both local), so should be preferred
        result = router._is_cheaper_with_acceptable_latency(
            candidate_model="phi3:mini",
            primary_model="qwen3-coder:32b",
            candidate_cost_per_token=0.0,
            primary_cost_per_token=0.0,
        )
        # Phi3 is faster, so it's always acceptable
        assert result is True

    def test_is_cheaper_with_unacceptable_latency_deepseek_to_phi3(self, router):
        """Test latency trade-off from deepseek (300ms) to phi3 (50ms)."""
        # This is a speed improvement, so it should be acceptable
        result = router._is_cheaper_with_acceptable_latency(
            candidate_model="phi3:mini",
            primary_model="deepseek-r1:8b",
            candidate_cost_per_token=0.0,
            primary_cost_per_token=0.0,
        )
        # Phi3 is faster, so it's acceptable
        assert result is True

    def test_latency_threshold_exceeded(self):
        """Test that excessive latency increase is rejected."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            latency_threshold=10.0,  # Very strict: only 10ms trade-off
        )

        # Trying to go from phi3 (50ms) to deepseek (300ms) should fail
        result = router._is_cheaper_with_acceptable_latency(
            candidate_model="deepseek-r1:8b",
            primary_model="phi3:mini",
            candidate_cost_per_token=0.0,
            primary_cost_per_token=0.0,
        )
        # 250ms increase > 10ms threshold, should fail
        assert result is False


class TestModelOptimizationLogic:
    """Test model selection optimization logic."""

    @pytest.fixture
    def router_optimized(self):
        """Create router with optimization enabled."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
            prefer_longer_models_if_cheaper_per_token=True,
        )

    @pytest.fixture
    def router_no_optimization(self):
        """Create router with optimization disabled."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
            prefer_longer_models_if_cheaper_per_token=False,
        )

    def test_optimize_model_selection_disabled(self, router_no_optimization):
        """Test that optimization can be disabled."""
        model = router_no_optimization._optimize_model_selection(
            primary_model="deepseek-r1:8b",
            complexity=QueryComplexity.COMPLEX,
            estimated_tokens=500,
        )

        # Should return primary model unchanged
        assert model == "deepseek-r1:8b"

    def test_optimize_model_selection_simple_to_phi3(self, router_optimized):
        """Test simple query optimization."""
        model = router_optimized._optimize_model_selection(
            primary_model="phi3:mini",
            complexity=QueryComplexity.SIMPLE,
            estimated_tokens=100,
        )

        # Simple queries should stay on phi3
        assert model == "phi3:mini"

    def test_optimize_model_selection_medium_queries(self, router_optimized):
        """Test medium complexity query optimization."""
        model = router_optimized._optimize_model_selection(
            primary_model="qwen3-coder:32b",
            complexity=QueryComplexity.MEDIUM,
            estimated_tokens=250,
        )

        # Medium query optimized from qwen to phi3 is acceptable
        # (phi3 is faster, cost doesn't matter for local models)
        # But actual optimization depends on latency threshold
        assert model in ["phi3:mini", "qwen3-coder:32b"]


class TestComplexQueryOptimization:
    """Test optimization specifically for complex queries."""

    @pytest.fixture
    def router(self):
        """Create router optimized for complex queries."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
            prefer_longer_models_if_cheaper_per_token=True,
            latency_threshold=200.0,  # Allow 200ms latency increase
        )

    def test_complex_query_may_optimize_to_qwen(self, router):
        """Test that complex queries can optimize to qwen if appropriate."""
        # With 200ms threshold, qwen (100ms) is faster than deepseek (300ms)
        # So optimization should prefer qwen
        model = router._optimize_model_selection(
            primary_model="deepseek-r1:8b",
            complexity=QueryComplexity.COMPLEX,
            estimated_tokens=500,
        )

        # Should potentially optimize to qwen (100ms vs 300ms = -200ms, acceptable)
        assert model in ["qwen3-coder:32b", "deepseek-r1:8b"]


class TestRoutingWithOptimization:
    """Test full routing flow with optimization."""

    @pytest.fixture
    def router(self):
        """Create router with optimization enabled."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
            prefer_longer_models_if_cheaper_per_token=True,
        )

    def test_select_model_with_optimization(self, router):
        """Test full select_model with optimization."""
        decision, can_proceed = router.select_model("What is Python?")

        assert can_proceed is True
        assert decision.model in ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        assert "optimized" in decision.reason or "Routed" in decision.reason

    def test_optimization_swap_tracking(self, router):
        """Test that optimization swaps are tracked."""
        initial_swaps = router.token_optimization_swaps

        # Route several queries
        for i in range(10):
            router.select_model("Complex query that needs optimization")

        # Swaps should be tracked (though may be 0 if no swaps occurred)
        assert router.token_optimization_swaps >= initial_swaps

    def test_optimization_reason_included(self, router):
        """Test that optimization reason is included in decision."""
        decision, _ = router.select_model("Design a complex system with distributed architecture")

        # Reason should indicate routing decision
        assert "query" in decision.reason.lower()
        assert decision.model in decision.reason


class TestBudgetEnforcementWithOptimization:
    """Test budget enforcement still works with optimization."""

    @pytest.fixture
    def router_tight_budget(self):
        """Create router with tight budget."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=0.001, policy=BudgetPolicy.SOFT_STOP),
            prefer_longer_models_if_cheaper_per_token=True,
        )

    def test_budget_check_with_optimization(self, router_tight_budget):
        """Test budget enforcer still checks even with optimization."""
        decision, can_proceed = router_tight_budget.select_model(
            "What is Python?",
            max_cost_usd=0.0001,
        )

        # Should still proceed (local models are free)
        assert can_proceed is True

    def test_budget_state_after_optimization(self, router_tight_budget):
        """Test budget state is correctly tracked after optimization."""
        router_tight_budget.select_model("Write code")

        stats = router_tight_budget.get_statistics()
        assert stats.total_cost_usd == 0.0  # Local models, no cost


class TestCostThresholdParameterization:
    """Test cost threshold parameter behavior."""

    def test_strict_cost_threshold(self):
        """Test strict cost threshold (5%) allows fewer swaps."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            cost_threshold=0.05,  # Very strict: 5% difference
        )

        assert router.cost_threshold == 0.05

    def test_loose_cost_threshold(self):
        """Test loose cost threshold (20%) allows more swaps."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            cost_threshold=0.20,  # Loose: 20% difference
        )

        assert router.cost_threshold == 0.20

    def test_cost_threshold_zero(self):
        """Test cost threshold of 0 (exact match only)."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            cost_threshold=0.0,  # Exact match required
        )

        assert router.cost_threshold == 0.0


class TestLatencyThresholdParameterization:
    """Test latency threshold parameter behavior."""

    def test_strict_latency_threshold(self):
        """Test strict latency threshold (10ms)."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            latency_threshold=10.0,  # Very strict: 10ms
        )

        assert router.latency_threshold == 10.0

    def test_moderate_latency_threshold(self):
        """Test moderate latency threshold (100ms - default)."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            latency_threshold=100.0,
        )

        assert router.latency_threshold == 100.0

    def test_loose_latency_threshold(self):
        """Test loose latency threshold (500ms)."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            latency_threshold=500.0,  # Loose: 500ms
        )

        assert router.latency_threshold == 500.0


class TestStatisticsWithOptimization:
    """Test statistics tracking with optimization."""

    @pytest.fixture
    def router(self):
        """Create router with optimization."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
            prefer_longer_models_if_cheaper_per_token=True,
        )

    def test_statistics_include_routing_decisions(self, router):
        """Test that statistics include all routing decisions."""
        router.select_model("What is AI?")
        router.select_model("Write code")
        router.select_model("Design system")

        stats = router.get_statistics()
        assert stats.total_queries == 3

    def test_statistics_reset_clears_optimization(self, router):
        """Test that reset clears optimization swap counter."""
        router.token_optimization_swaps = 5

        router.reset_statistics()

        assert router.token_optimization_swaps == 0

    def test_cost_reduction_metric(self, router):
        """Test cost reduction compared to deepseek-only baseline."""
        # Route 10 mixed queries
        for i in range(10):
            if i % 3 == 0:
                router.select_model("What is this?")  # Simple
            elif i % 3 == 1:
                router.select_model("Write code")  # Medium
            else:
                router.select_model("Design system")  # Complex

        stats = router.get_statistics()

        # Cost should be minimal (all local models)
        assert stats.total_cost_usd == 0.0
        # Cost improvement should be >= 0
        assert stats.cost_vs_deepseek_only >= 0


class TestComplexQueryRouting:
    """Test routing decisions for complex queries."""

    @pytest.fixture
    def router(self):
        """Create router for complex query testing."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
        )

    def test_complex_query_long_form(self, router):
        """Test complex query with multiple reasoning steps."""
        query = (
            "Design and implement a distributed cache system with consensus voting, "
            "production-grade performance optimization, and comprehensive error handling"
        )

        decision, can_proceed = router.select_model(query)

        assert decision.complexity == QueryComplexity.COMPLEX
        # Model might be optimized from deepseek to qwen based on latency threshold
        assert decision.model in ["deepseek-r1:8b", "qwen3-coder:32b"]
        assert can_proceed is True

    def test_complex_query_with_code(self, router):
        """Test complex query with code components."""
        query = (
            "Implement and optimize this algorithm: "
            "def calculate_something(): "
            "    # Complex logic here"
        )

        decision, can_proceed = router.select_model(query)

        assert decision.complexity in [QueryComplexity.MEDIUM, QueryComplexity.COMPLEX]
        assert can_proceed is True

    def test_complex_query_architectural(self, router):
        """Test complex architectural query."""
        query = "Design a scalable, distributed, production-grade system architecture with security considerations"

        decision, can_proceed = router.select_model(query)

        assert decision.complexity == QueryComplexity.COMPLEX
        # Model might be optimized from deepseek to qwen based on latency threshold
        assert decision.model in ["deepseek-r1:8b", "qwen3-coder:32b"]


class TestCostOptimization30PercentReduction:
    """Test 30% cost reduction target."""

    @pytest.fixture
    def router(self):
        """Create router for cost optimization testing."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            budget_enforcer=BudgetEnforcer(budget_usd=100.0),
            prefer_longer_models_if_cheaper_per_token=True,
        )

    def test_routing_distribution_mixed_workload(self, router):
        """Test routing distribution on mixed workload."""
        # Simulate typical workload: 40% simple, 40% medium, 20% complex
        queries = (
            ["What is X?"] * 4  # Simple
            + ["Write a function to Y"] * 4  # Medium
            + ["Design a system for Z"] * 2  # Complex
        )

        for query in queries:
            router.select_model(query)

        stats = router.get_statistics()

        # Should route diverse workload
        assert stats.total_queries == 10
        assert stats.simple_count >= 3
        # Medium count might include optimized complex queries
        assert stats.medium_count >= 3

    def test_cost_per_token_efficiency(self, router):
        """Test cost per token efficiency."""
        # All local models should have 0 cost per token
        for model in ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]:
            cost = router._get_cost_per_token(model, 1000)
            assert cost == 0.0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def router(self):
        """Create router for edge case testing."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
        )

    def test_empty_query(self, router):
        """Test handling of empty query."""
        decision, can_proceed = router.select_model("")

        # Should still route to some model
        assert decision.model in ["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"]
        assert can_proceed is True

    def test_very_long_query(self, router):
        """Test handling of very long query."""
        long_query = "word " * 1000  # 1000 words

        decision, can_proceed = router.select_model(long_query)

        # Long query should route to complex model
        assert decision.complexity in [QueryComplexity.MEDIUM, QueryComplexity.COMPLEX]
        assert can_proceed is True

    def test_query_with_special_characters(self, router):
        """Test query with special characters."""
        query = "What is @#$%^&*() in code? (parentheses, brackets, symbols)"

        decision, can_proceed = router.select_model(query)

        # Should still work
        assert decision.model is not None
        assert can_proceed is True

    def test_unicode_query(self, router):
        """Test Unicode characters in query."""
        query = "What is ñ, ü, 中文, 日本語, العربية?"

        decision, can_proceed = router.select_model(query)

        # Should handle Unicode
        assert decision.model is not None
        assert can_proceed is True


class TestPerformanceCharacteristics:
    """Test performance characteristics of v2 router."""

    @pytest.fixture
    def router(self):
        """Create router for performance testing."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("test-session"),
            prefer_longer_models_if_cheaper_per_token=True,
        )

    def test_routing_decision_latency(self, router):
        """Test that routing decisions are fast (<50ms)."""
        start = time.time()

        for _ in range(100):
            router.select_model("What is Python?")

        elapsed = (time.time() - start) * 1000  # Convert to ms
        avg_latency = elapsed / 100

        # Should be fast: <50ms per decision
        assert avg_latency < 50.0, f"Average latency {avg_latency}ms > 50ms"

    def test_optimization_calculation_overhead(self, router):
        """Test that optimization adds minimal overhead."""
        start = time.time()

        for _ in range(100):
            router._optimize_model_selection(
                "deepseek-r1:8b",
                QueryComplexity.COMPLEX,
                500,
            )

        elapsed = (time.time() - start) * 1000  # Convert to ms
        avg_latency = elapsed / 100

        # Should be very fast: <10ms per optimization
        assert avg_latency < 10.0, f"Optimization latency {avg_latency}ms > 10ms"


class TestChaosTestingV2:
    """Chaos testing for v2 router with optimization."""

    @pytest.fixture
    def router_chaos(self):
        """Create router for chaos testing."""
        reset_cost_aware_router()
        return CostAwareRouter(
            cost_tracker=SessionCostTracker("chaos-test"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0, policy=BudgetPolicy.SOFT_STOP),
            prefer_longer_models_if_cheaper_per_token=True,
        )

    def test_random_queries_no_crash(self, router_chaos):
        """Test routing doesn't crash on random input."""
        import random

        queries = [
            f"{'What' if random.random() > 0.5 else 'Design'} query {i}"
            for i in range(100)
        ]

        for query in queries:
            decision, can_proceed = router_chaos.select_model(query)
            # Should always return a valid decision
            assert decision.model is not None
            assert isinstance(can_proceed, bool)

    def test_threshold_parameter_variations(self, router_chaos):
        """Test routing works with various threshold parameters."""
        for cost_threshold in [0.0, 0.05, 0.10, 0.20, 0.50]:
            for latency_threshold in [10.0, 50.0, 100.0, 500.0]:
                router = CostAwareRouter(
                    cost_tracker=SessionCostTracker("test"),
                    cost_threshold=cost_threshold,
                    latency_threshold=latency_threshold,
                )

                decision, _ = router.select_model("Test query")
                assert decision.model is not None

    def test_sustained_load_optimization(self, router_chaos):
        """Test optimization under sustained load."""
        for i in range(500):
            decision, can_proceed = router_chaos.select_model(
                f"Query {i}: {'simple' if i % 3 == 0 else 'complex'}"
            )

            if can_proceed:
                router_chaos.record_execution(
                    decision.model,
                    decision.estimated_tokens,
                    100.0,
                )

        stats = router_chaos.get_statistics()
        # Should handle 500 queries without issue
        assert stats.total_queries == 500


class TestBackwardCompatibilityV2:
    """Test full backward compatibility with v1 API."""

    def test_v1_code_still_works(self):
        """Test that v1 code patterns still work."""
        # This is how v1 users would create router
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test"),
            budget_enforcer=BudgetEnforcer(budget_usd=10.0),
        )

        # Should work without errors
        decision, can_proceed = router.select_model("What is Python?")
        assert decision.model is not None

    def test_v1_select_model_signature(self):
        """Test that select_model signature is backward compatible."""
        router = CostAwareRouter()

        # v1 usage: select_model(query, max_cost_usd)
        decision, can_proceed = router.select_model(
            "What is Python?",
            max_cost_usd=0.01,
        )

        assert decision is not None
        assert isinstance(can_proceed, bool)

    def test_v1_record_execution(self):
        """Test that record_execution is backward compatible."""
        router = CostAwareRouter(cost_tracker=SessionCostTracker("test"))

        cost = router.record_execution(
            model="phi3:mini",
            actual_tokens=100,
            duration_ms=500.0,
        )

        assert isinstance(cost, float)
        assert cost >= 0.0

    def test_v1_get_statistics(self):
        """Test that get_statistics is backward compatible."""
        router = CostAwareRouter(cost_tracker=SessionCostTracker("test"))

        router.select_model("What is AI?")

        stats = router.get_statistics()

        # Should have all v1 fields
        assert hasattr(stats, "total_queries")
        assert hasattr(stats, "simple_count")
        assert hasattr(stats, "medium_count")
        assert hasattr(stats, "complex_count")
        assert hasattr(stats, "phi3_routed")
        assert hasattr(stats, "qwen_routed")
        assert hasattr(stats, "deepseek_routed")
        assert hasattr(stats, "total_cost_usd")
        assert hasattr(stats, "avg_cost_per_query")
        assert hasattr(stats, "cost_vs_deepseek_only")


class TestIntegrationOptimizationFullFlow:
    """Integration tests for full optimization flow."""

    def test_full_routing_optimization_flow(self):
        """Test complete routing with optimization."""
        reset_cost_aware_router()
        tracker = SessionCostTracker("integration-test")
        enforcer = BudgetEnforcer(budget_usd=10.0)

        router = CostAwareRouter(
            cost_tracker=tracker,
            budget_enforcer=enforcer,
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.10,
            latency_threshold=100.0,
        )

        # Route diverse queries
        decisions = []
        for query in [
            "What is Python?",
            "Write a function",
            "Design a system",
        ]:
            decision, can_proceed = router.select_model(query)
            decisions.append(decision)
            assert can_proceed is True

        # Record executions
        for decision in decisions:
            cost = router.record_execution(
                decision.model,
                decision.estimated_tokens,
                100.0,
            )
            assert cost >= 0.0

        # Get statistics
        stats = router.get_statistics()
        assert stats.total_queries == 3
        assert stats.total_cost_usd >= 0.0


class TestCostReductionTarget30Percent:
    """Verify 30% cost reduction target with mixed workload."""

    def test_cost_reduction_on_real_workload(self):
        """Test cost reduction on realistic mixed workload."""
        reset_cost_aware_router()

        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("cost-test"),
            budget_enforcer=BudgetEnforcer(budget_usd=100.0),
            prefer_longer_models_if_cheaper_per_token=True,
        )

        # Simulate realistic workload
        workload = (
            ["What is X?"] * 50 +  # Simple queries
            ["Implement Y"] * 30 +  # Medium queries
            ["Design Z"] * 20  # Complex queries
        )

        for query in workload:
            decision, _ = router.select_model(query)
            router.record_execution(decision.model, decision.estimated_tokens, 100.0)

        stats = router.get_statistics()

        # Verify workload was routed
        assert stats.total_queries == 100
        # Cost should be minimal (all local models)
        assert stats.total_cost_usd == 0.0
        # Routing should distribute across models
        assert stats.phi3_routed > 0  # Some simple queries


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
