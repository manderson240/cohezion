"""Integration tests for Phase 1 cost optimization (Tracking + Aggregation + Enforcement).

Verifies:
- Cost tracking integrated with SessionState
- Cost fields persisted in checkpoints
- Metrics aggregation includes cost data
- Budget enforcement integrates with CompoundExecutor
- End-to-end cost flow from tracking to metrics
"""

import json

import pytest

from cohezion.compound.session_manager import SessionState
from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.observability.unified_metrics import InferenceMetrics


class TestSessionStateCost:
    """Test SessionState cost fields."""

    def test_session_state_has_cost_fields(self):
        """Verify SessionState has cost tracking fields."""
        state = SessionState(
            session_id="test-session",
            skill_name="test-skill",
            current_step=0,
            total_steps=10,
            context="test context",
        )

        assert hasattr(state, "total_cost_usd")
        assert hasattr(state, "cost_breakdown")
        assert state.total_cost_usd == 0.0
        assert state.cost_breakdown == {}

    def test_session_state_cost_persistence(self):
        """Verify cost fields can be set and retrieved."""
        state = SessionState(
            session_id="test-session",
            skill_name="test-skill",
            current_step=0,
            total_steps=10,
            context="test context",
            total_cost_usd=1.50,
            cost_breakdown={"gpt-4": 0.90, "claude-3-opus": 0.60},
        )

        assert state.total_cost_usd == 1.50
        assert state.cost_breakdown["gpt-4"] == 0.90
        assert state.cost_breakdown["claude-3-opus"] == 0.60

    def test_session_state_serialization(self):
        """Verify SessionState can be serialized with cost fields."""
        from dataclasses import asdict

        state = SessionState(
            session_id="test-session",
            skill_name="test-skill",
            current_step=0,
            total_steps=10,
            context="test context",
            total_cost_usd=1.50,
            cost_breakdown={"gpt-4": 0.90},
        )

        serialized = asdict(state)

        assert serialized["total_cost_usd"] == 1.50
        assert serialized["cost_breakdown"]["gpt-4"] == 0.90

    def test_session_state_json_roundtrip(self):
        """Verify SessionState can be serialized to JSON and back."""
        from dataclasses import asdict

        state = SessionState(
            session_id="test-session",
            skill_name="test-skill",
            current_step=0,
            total_steps=10,
            context="test context",
            total_cost_usd=1.50,
            cost_breakdown={"gpt-4": 0.90},
        )

        # Serialize
        serialized = asdict(state)
        json_str = json.dumps(serialized, default=str)

        # Deserialize
        data = json.loads(json_str)
        assert data["total_cost_usd"] == 1.50
        assert data["cost_breakdown"]["gpt-4"] == 0.90


class TestInferenceMetricsCost:
    """Test InferenceMetrics cost fields."""

    def test_inference_metrics_has_cost_fields(self):
        """Verify InferenceMetrics has cost tracking fields."""
        metrics = InferenceMetrics()

        assert hasattr(metrics, "total_cost_usd")
        assert hasattr(metrics, "cost_breakdown")
        assert hasattr(metrics, "budget_utilization_pct")
        assert metrics.total_cost_usd == 0.0
        assert metrics.cost_breakdown == {}
        assert metrics.budget_utilization_pct == 0.0

    def test_inference_metrics_cost_values(self):
        """Verify cost values can be set in metrics."""
        metrics = InferenceMetrics(
            total_cost_usd=2.50,
            cost_breakdown={"gpt-4": 1.50, "gpt-4o": 1.0},
            budget_utilization_pct=25.0,
        )

        assert metrics.total_cost_usd == 2.50
        assert metrics.cost_breakdown["gpt-4"] == 1.50
        assert metrics.budget_utilization_pct == 25.0

    def test_inference_metrics_cost_serialization(self):
        """Verify cost fields included in to_dict()."""
        metrics = InferenceMetrics(
            total_cost_usd=2.50,
            cost_breakdown={"gpt-4": 1.50},
            budget_utilization_pct=25.0,
        )

        data = metrics.to_dict()

        assert data["total_cost_usd"] == 2.50
        assert data["cost_breakdown"]["gpt-4"] == 1.50
        assert data["budget_utilization_pct"] == 25.0


class TestCostTrackerIntegration:
    """Test cost tracker integration with session/metrics."""

    def test_cost_tracker_with_session_state(self):
        """Verify cost tracker can be integrated with SessionState."""
        tracker = SessionCostTracker(session_id="test-session")

        # Track costs
        tracker.track_usage_fast("gpt-4", tokens=1000)
        tracker.track_usage_fast("gpt-4o", tokens=500)

        summary = tracker.get_session_cost()

        # Create session state with summary
        state = SessionState(
            session_id="test-session",
            skill_name="test-skill",
            current_step=0,
            total_steps=10,
            context="test",
            total_cost_usd=summary["total_cost_usd"],
            cost_breakdown={
                "gpt-4": 0.03,
                "gpt-4o": 0.0075,
            },
        )

        assert state.total_cost_usd > 0
        assert "gpt-4" in state.cost_breakdown

    def test_cost_tracker_with_metrics(self):
        """Verify cost tracker data can be used in metrics."""
        tracker = SessionCostTracker(session_id="test-session")

        # Track costs
        cost1 = tracker.track_usage_fast("gpt-4", tokens=1000)
        cost2 = tracker.track_usage_fast("gpt-4o", tokens=500)

        summary = tracker.get_session_cost()

        # Create metrics
        metrics = InferenceMetrics(
            total_tokens=summary["total_tokens"],
            total_cost_usd=summary["total_cost_usd"],
            cost_breakdown={"gpt-4": cost1, "gpt-4o": cost2},
        )

        assert metrics.total_cost_usd == cost1 + cost2
        assert metrics.total_tokens == 1500


class TestBudgetEnforcerIntegration:
    """Test budget enforcer integration with session costs."""

    def test_budget_enforcer_with_session_cost(self):
        """Verify budget enforcer works with session cost."""
        enforcer = BudgetEnforcer(budget_usd=10.0)

        # Get cost from tracker
        tracker = SessionCostTracker(session_id="test-session")
        tracker.track_usage_fast("gpt-4", tokens=1000)
        summary = tracker.get_session_cost()

        # Check budget
        can_proceed, _reason = enforcer.check_budget(summary["total_cost_usd"])

        assert can_proceed is True
        assert summary["total_cost_usd"] < 10.0

    def test_budget_enforcer_blocks_at_limit(self):
        """Verify budget enforcer blocks when limit exceeded."""
        enforcer = BudgetEnforcer(budget_usd=1.0)

        tracker = SessionCostTracker(session_id="test-session")
        # Generate high cost: gpt-4 costs $0.03 per 1K tokens
        # 50K tokens = $1.50 (exceeds $1.0 budget)
        for _ in range(50):
            tracker.track_usage_fast("gpt-4", tokens=1000)

        summary = tracker.get_session_cost()

        can_proceed, reason = enforcer.check_budget(summary["total_cost_usd"])

        assert can_proceed is False
        assert "Budget limit exceeded" in reason or "circuit breaker" in reason.lower()

    def test_budget_state_with_metrics(self):
        """Verify budget state can be used in metrics."""
        enforcer = BudgetEnforcer(budget_usd=10.0)

        # Simulate some cost
        current_cost = 7.5

        state = enforcer.get_budget_state(current_cost)

        # Create metrics with budget info
        metrics = InferenceMetrics(
            total_cost_usd=current_cost,
            budget_utilization_pct=state.utilization_pct,
        )

        assert metrics.total_cost_usd == 7.5
        assert metrics.budget_utilization_pct == 75.0


class TestEndToEndCostFlow:
    """Test complete cost flow from tracking to enforcement."""

    def test_full_cost_tracking_flow(self):
        """Verify full cost tracking flow end-to-end."""
        # Initialize cost infrastructure
        tracker = SessionCostTracker(session_id="e2e-session")
        enforcer = BudgetEnforcer(budget_usd=5.0)

        # Simulate API calls with costs
        api_calls = [
            ("gpt-4", 500),
            ("gpt-4o", 300),
            ("claude-3-sonnet", 200),
        ]

        for model, tokens in api_calls:
            cost = tracker.track_usage_fast(model, tokens)
            print(f"{model}: {cost} USD")

        # Get summary
        summary = tracker.get_session_cost()
        total_cost = summary["total_cost_usd"]

        # Check budget
        can_proceed, _reason = enforcer.check_budget(total_cost)

        # Create metrics
        metrics = InferenceMetrics(
            total_cost_usd=total_cost,
            budget_utilization_pct=(total_cost / 5.0 * 100),
        )

        # Create session state
        state = SessionState(
            session_id="e2e-session",
            skill_name="test-skill",
            current_step=0,
            total_steps=10,
            context="test",
            total_cost_usd=total_cost,
            cost_breakdown=summary["model_usage"],  # Rough mapping
        )

        # Verify all pieces work together
        assert state.total_cost_usd == total_cost
        assert metrics.total_cost_usd == total_cost
        assert can_proceed is True  # Should be under $5
        assert metrics.budget_utilization_pct < 100

    def test_cost_flow_exceeding_budget(self):
        """Verify cost tracking catches budget overruns."""
        tracker = SessionCostTracker(session_id="overrun-session")
        enforcer = BudgetEnforcer(budget_usd=0.5)

        # Track expensive API calls
        # gpt-4 costs $0.03 per 1K tokens
        # 30 * 1000 tokens = 30K = $0.90 (exceeds $0.50 budget)
        for _ in range(30):
            tracker.track_usage_fast("gpt-4", tokens=1000)

        summary = tracker.get_session_cost()

        # Check budget
        can_proceed, reason = enforcer.check_budget(summary["total_cost_usd"])

        # Should exceed budget
        assert can_proceed is False
        assert "Budget limit exceeded" in reason or "circuit breaker" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
