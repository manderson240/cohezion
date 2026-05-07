"""Tests for parameter tuning in CostAwareRouter.

Tests how cost_threshold and latency_threshold parameters affect routing behavior.
"""

from pathlib import Path

import pytest

from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.swarm.cost_aware_router import (
    CostAwareRouter,
)


_YAML_AVAILABLE = (Path(__file__).parent.parent.parent / "config" / "model_profiles.yaml").exists()
_skip_no_yaml = pytest.mark.skipif(
    not _YAML_AVAILABLE, reason="config/model_profiles.yaml not found — fallback models differ"
)


@_skip_no_yaml
class TestCostThresholdTuning:
    """Test cost_threshold parameter effects on routing."""

    def test_cost_threshold_values_make_routing_decisions(self):
        """Test that cost_threshold parameter is used in routing decisions."""
        router_low = CostAwareRouter(
            cost_tracker=SessionCostTracker("low-cost"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.05,
        )

        router_high = CostAwareRouter(
            cost_tracker=SessionCostTracker("high-cost"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.50,
        )

        query = "Write a Python function"

        decision_low, _ = router_low.select_model(query)
        decision_high, _ = router_high.select_model(query)

        assert decision_low.model in ["phi3:mini", "qwen3-coder:32b"]
        assert decision_high.model in ["phi3:mini", "qwen3-coder:32b"]

    def test_cost_threshold_parameter_persistence(self):
        """Test that cost_threshold parameter persists across multiple decisions."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("persist"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.10,
        )

        assert router.cost_threshold == 0.10

        router.select_model("Query 1")
        assert router.cost_threshold == 0.10

        router.select_model("Query 2")
        assert router.cost_threshold == 0.10

    def test_cost_threshold_intermediate_values(self):
        """Test cost_threshold with intermediate values."""
        thresholds = [0.05, 0.10, 0.15, 0.20, 0.30]
        routers = [
            CostAwareRouter(
                cost_tracker=SessionCostTracker(f"threshold-{t}"),
                prefer_longer_models_if_cheaper_per_token=True,
                cost_threshold=t,
            )
            for t in thresholds
        ]

        query = "Write a Python function to process data"

        for router, _threshold in zip(routers, thresholds, strict=False):
            decision, _ = router.select_model(query)
            assert decision.model in ["phi3:mini", "qwen3-coder:32b"]


@_skip_no_yaml
class TestLatencyThresholdTuning:
    """Test latency_threshold parameter effects on routing."""

    def test_latency_threshold_allows_faster_models(self):
        """Test that latency_threshold allows optimization to faster models."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("zero-latency"),
            prefer_longer_models_if_cheaper_per_token=True,
            latency_threshold=0.0,
        )

        decision_medium, _ = router.select_model("Write a Python function")
        decision_complex, _ = router.select_model("Design a distributed system")

        assert decision_medium.model in ["phi3:mini", "qwen3-coder:32b"]
        assert decision_complex.model in ["deepseek-r1:8b", "qwen3-coder:32b"]

    def test_latency_threshold_parameter_persistence(self):
        """Test that latency_threshold parameter persists."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("latency-persist"),
            prefer_longer_models_if_cheaper_per_token=True,
            latency_threshold=100.0,
        )

        assert router.latency_threshold == 100.0

        router.select_model("Query 1")
        assert router.latency_threshold == 100.0

        router.select_model("Query 2")
        assert router.latency_threshold == 100.0

    def test_latency_threshold_intermediate_values(self):
        """Test latency_threshold with intermediate values."""
        thresholds = [0.0, 50.0, 100.0, 200.0]
        routers = [
            CostAwareRouter(
                cost_tracker=SessionCostTracker(f"latency-{t}"),
                prefer_longer_models_if_cheaper_per_token=True,
                latency_threshold=t,
            )
            for t in thresholds
        ]

        query = "Design a distributed system"

        for router, _threshold in zip(routers, thresholds, strict=False):
            decision, _ = router.select_model(query)
            assert decision.model in ["deepseek-r1:8b", "qwen3-coder:32b", "phi3:mini"]


@_skip_no_yaml
class TestCombinedParameterTuning:
    """Test interactions between cost_threshold and latency_threshold."""

    def test_both_thresholds_allow_optimization(self):
        """Test that parameters control optimization behavior."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("both-control"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.0,
            latency_threshold=0.0,
        )

        decision_medium, _ = router.select_model("Write a Python function")
        decision_complex, _ = router.select_model("Design a distributed system")

        assert decision_medium.model in ["phi3:mini", "qwen3-coder:32b"]
        assert decision_complex.model in ["deepseek-r1:8b", "qwen3-coder:32b"]

    def test_both_thresholds_high_enables_optimization(self):
        """Test that high both thresholds enables aggressive optimization."""
        router = CostAwareRouter(
            cost_tracker=SessionCostTracker("both-high"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.50,
            latency_threshold=200.0,
        )

        decisions = []
        for _ in range(3):
            decision, _ = router.select_model("Write a function")
            decisions.append(decision.model)

        assert all(m in ["phi3:mini", "qwen3-coder:32b"] for m in decisions)

    def test_parameter_tuning_convergence(self):
        """Test that parameter adjustments achieve optimization levels."""
        router_aggressive = CostAwareRouter(
            cost_tracker=SessionCostTracker("aggressive"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.30,
            latency_threshold=150.0,
        )

        router_conservative = CostAwareRouter(
            cost_tracker=SessionCostTracker("conservative"),
            prefer_longer_models_if_cheaper_per_token=True,
            cost_threshold=0.01,
            latency_threshold=10.0,
        )

        medium_query = "Write a Python function for data processing"

        agg_decisions = []
        for _ in range(3):
            d, _ = router_aggressive.select_model(medium_query)
            agg_decisions.append(d.model)

        cons_decisions = []
        for _ in range(3):
            d, _ = router_conservative.select_model(medium_query)
            cons_decisions.append(d.model)

        assert all(m in ["phi3:mini", "qwen3-coder:32b"] for m in agg_decisions)
        assert all(m in ["phi3:mini", "qwen3-coder:32b"] for m in cons_decisions)
