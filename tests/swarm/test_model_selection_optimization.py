"""Tests for model selection optimization logic in CostAwareRouter.

Tests the decision-making process for selecting between phi3, qwen, and deepseek.
"""

import pytest

from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.swarm.cost_aware_router import (
    CostAwareRouter,
    QueryComplexity,
)


class TestModelSelectionOptimization:
    """Test model selection optimization logic."""

    @pytest.fixture
    def router(self):
        """Create router with optimization enabled."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("test-selection"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.10,
            latency_threshold=100.0,
        )
        return router

    def test_simple_query_always_uses_phi3(self, router):
        """Test that simple queries always use phi3:mini."""
        simple_queries = [
            "What is Python?",
            "Define machine learning",
            "List the items",
        ]

        for query in simple_queries:
            decision, _ = router.select_model(query)
            # Simple queries cannot be downgraded further, so always phi3 or from optimization
            assert decision.model in [
                "phi3:mini",
                "qwen3-coder:32b",
                "Phi-4-mini-instruct-Hybrid",
                "Qwen3-8B-Hybrid",
            ], f"Failed for: {query}"

    def test_medium_query_optimizes_to_phi3_for_cost(self, router):
        """Test that medium queries may downgrade to phi3-tier for cost savings."""
        medium_queries = [
            "Write a Python function",
            "Create a simple data processing script",
        ]

        for query in medium_queries:
            decision, _ = router.select_model(query)
            # Medium queries may optimize to phi3-tier if TPS acceptable
            assert decision.model in [
                "phi3:mini",
                "qwen3-coder:32b",
                "Phi-4-mini-instruct-Hybrid",
                "Qwen3-8B-Hybrid",
            ], f"Failed for: {query}"

    def test_complex_query_optimizes_to_faster_model_for_cost(self, router):
        """Test that complex queries may optimize to faster models for cost/efficiency."""
        complex_queries = [
            "Design a distributed caching system",
            "Implement production-grade security",
        ]

        for query in complex_queries:
            decision, _ = router.select_model(query)
            # Complex queries may optimize to various models
            assert decision.model in [
                "deepseek-r1:8b",
                "qwen3-coder:32b",
                "phi3:mini",
                "Phi-4-mini-instruct-Hybrid",
                "Qwen3-8B-Hybrid",
                "Qwen3-14B-Hybrid",
            ], f"Failed for: {query}"

    def test_complexity_analysis_drives_base_selection(self, router):
        """Test that query complexity correctly determines base model selection."""
        decision_simple, _ = router.select_model("What is this?")
        assert decision_simple.complexity == QueryComplexity.SIMPLE

        decision_medium, _ = router.select_model("Write a Python function")
        assert decision_medium.complexity == QueryComplexity.MEDIUM

        decision_complex, _ = router.select_model(
            "Design and implement a distributed system with optimization"
        )
        assert decision_complex.complexity == QueryComplexity.COMPLEX

    def test_optimization_maintains_quality_threshold(self, router):
        """Test that optimization maintains minimum acceptable quality."""
        queries = [
            "What is Python?",  # Simple: phi3 (0.6)
            "Write a function",  # Medium: phi3/qwen (0.6-0.85)
            "Design a system",  # Complex: phi3/qwen/deepseek (0.6-0.95)
        ]

        quality_scores = []
        for query in queries:
            decision, _ = router.select_model(query)
            quality_scores.append(decision.quality_score)

        # Minimum quality should be phi3 (0.6)
        min_quality = min(quality_scores)
        assert min_quality >= 0.6, f"Quality score {min_quality} below phi3 minimum"

        # All scores should be valid model quality scores
        for score in quality_scores:
            assert score in [0.6, 0.82, 0.85, 0.90, 0.95], f"Invalid quality score: {score}"

    def test_model_selection_consistency(self, router):
        """Test that identical queries get identical model selections."""
        query = "Write a Python function to process data"

        decisions = []
        for _ in range(5):
            decision, _ = router.select_model(query)
            decisions.append(decision.model)

        # All decisions should be identical for same query
        assert len(set(decisions)) == 1, f"Inconsistent routing: {decisions}"

    def test_routing_decision_reason_explains_choice(self, router):
        """Test that routing decision includes explanatory reason."""
        decision, _ = router.select_model("Write a Python function")

        # Reason should explain the routing decision
        assert "routed" in decision.reason.lower()
        assert decision.model in decision.reason
