"""Tests for cost optimization module.

Tests cost tracking, budget enforcement, and cost-aware routing.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from cohezion.compound.models import ExecutionMetrics
from cohezion.research.cost_optimization import (
    CostAwareRouter,
    CostBudget,
    CostTracker,
    ExperimentCost,
    create_cost_tracker,
    estimate_experiment_cost,
    get_cheapest_model,
)


class TestCostBudget:
    """Tests for CostBudget."""

    def test_default_budget_creation(self):
        """[COST-01] Default budget created with sensible values."""
        budget = CostBudget()

        assert budget.max_cost_usd == 100.0
        assert budget.max_tokens == 1_000_000
        assert budget.max_experiments == 100
        assert budget.warning_threshold == 0.8
        assert budget.hard_limit is True

    def test_budget_within_limits(self):
        """[COST-02] Budget allows operations within limits."""
        budget = CostBudget(max_cost_usd=10.0)

        within, status = budget.is_within_budget(
            current_cost=5.0,
            current_tokens=1000,
            current_experiments=10,
        )

        assert within is True
        assert status["cost_ok"] is True
        assert status["cost_percent"] == 0.5

    def test_budget_exceeds_cost_limit(self):
        """[COST-03] Budget blocks when cost limit exceeded."""
        budget = CostBudget(max_cost_usd=10.0, hard_limit=True)

        within, status = budget.is_within_budget(
            current_cost=15.0,
            current_tokens=1000,
            current_experiments=10,
        )

        assert within is False
        assert status["cost_ok"] is False

    def test_budget_warning_threshold(self):
        """[COST-04] Budget triggers warning at threshold."""
        budget = CostBudget(max_cost_usd=10.0, warning_threshold=0.8)

        within, status = budget.is_within_budget(
            current_cost=8.5,  # 85% - above threshold
            current_tokens=1000,
            current_experiments=10,
        )

        assert within is True  # Still allowed
        assert status["warning_triggered"] is True


class TestCostTracker:
    """Tests for CostTracker."""

    def test_cost_calculation(self):
        """[COST-05] Cost calculation uses correct rates."""
        tracker = CostTracker()

        # Ollama models are free
        cost = tracker.calculate_cost(1000, "ollama/phi3:mini")
        assert cost == 0.0

        # Claude Haiku: $0.25 per 1K tokens
        cost = tracker.calculate_cost(1000, "anthropic/claude-3-haiku")
        assert cost == 0.25

        # Claude Sonnet: $3.00 per 1K tokens
        cost = tracker.calculate_cost(2000, "anthropic/claude-3-sonnet")
        assert cost == 6.0

    def test_record_experiment(self):
        """[COST-06] Recording experiment updates totals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(max_cost_usd=100.0),
                log_file=Path(tmpdir) / "costs.jsonl",
            )

            metrics = ExecutionMetrics(total_tokens=1000, duration_seconds=1.0)
            exp_cost = tracker.record_experiment("exp-1", metrics, "ollama/phi3:mini")

            assert tracker.total_cost == 0.0  # Free model
            assert tracker.total_tokens == 1000
            assert tracker.total_experiments == 1
            assert isinstance(exp_cost, ExperimentCost)

    def test_cost_report(self):
        """[COST-07] Cost report contains all metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(max_cost_usd=100.0),
                log_file=Path(tmpdir) / "costs.jsonl",
            )

            # Record some experiments
            for i in range(3):
                metrics = ExecutionMetrics(total_tokens=1000, duration_seconds=1.0)
                tracker.record_experiment(f"exp-{i}", metrics, "ollama/phi3:mini")

            report = tracker.get_cost_report()

            assert report["total_experiments"] == 3
            assert report["total_tokens"] == 3000
            assert report["within_budget"] is True
            assert "usage_percent" in report
            assert "per_model" in report


class TestCostAwareRouter:
    """Tests for CostAwareRouter."""

    def test_select_preferred_model_under_budget(self):
        """[COST-08] Uses preferred model when under budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(max_cost_usd=100.0),
                log_file=Path(tmpdir) / "costs.jsonl",
            )
            router = CostAwareRouter(tracker, cost_threshold=0.9)

            model = router.select_model("anthropic/claude-3-sonnet", complexity=0.5)
            assert model == "anthropic/claude-3-sonnet"

    def test_downgrade_when_over_threshold(self):
        """[COST-09] Downgrades model when over threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(max_cost_usd=10.0),
                log_file=Path(tmpdir) / "costs.jsonl",
            )

            # Simulate high usage
            tracker.total_cost = 9.5  # 95% of budget
            router = CostAwareRouter(tracker, cost_threshold=0.9)

            # Should downgrade from expensive to cheaper
            model = router.select_model("anthropic/claude-3-sonnet", complexity=0.5)
            assert model != "anthropic/claude-3-sonnet"  # Should downgrade
            assert "claude-3-haiku" in model or "gpt-4o-mini" in model or "ollama" in model

    def test_should_continue_within_budget(self):
        """[COST-10] Continue when within budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(max_cost_usd=100.0),
                log_file=Path(tmpdir) / "costs.jsonl",
            )
            router = CostAwareRouter(tracker)

            should_continue, reason = router.should_continue()
            assert should_continue is True
            assert "Within budget" in reason


class TestCostUtilities:
    """Tests for utility functions."""

    def test_estimate_experiment_cost(self):
        """[COST-11] Cost estimation works correctly."""
        cost = estimate_experiment_cost("anthropic/claude-3-haiku", tokens=2000)
        assert cost == 0.5  # 2K tokens at $0.25 per 1K

        cost = estimate_experiment_cost("ollama/phi3:mini", tokens=5000)
        assert cost == 0.0  # Free

    def test_get_cheapest_model(self):
        """[COST-12] Finds cheapest model from list."""
        models = [
            "anthropic/claude-3-sonnet",
            "anthropic/claude-3-haiku",
            "ollama/phi3:mini",
        ]
        cheapest = get_cheapest_model(models)
        assert cheapest == "ollama/phi3:mini"  # Free

    def test_create_cost_tracker(self):
        """[COST-13] Factory creates tracker with correct budget."""
        tracker = create_cost_tracker(max_cost=50.0, max_experiments=20)

        assert tracker.budget.max_cost_usd == 50.0
        assert tracker.budget.max_experiments == 20


class TestCostIntegration:
    """Integration tests for cost optimization."""

    def test_full_cost_session(self):
        """[COST-14] Full session with cost tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(max_cost_usd=10.0, max_experiments=5),
                log_file=Path(tmpdir) / "costs.jsonl",
            )
            router = CostAwareRouter(tracker)

            # Simulate experiments
            for i in range(5):
                # Select model
                model = router.select_model("anthropic/claude-3-haiku", complexity=0.5)

                # Record cost
                tokens = 1000 + i * 500
                metrics = ExecutionMetrics(total_tokens=tokens, duration_seconds=1.0)
                tracker.record_experiment(f"exp-{i}", metrics, model)

                # Check if should continue
                should_continue, _ = router.should_continue()
                if not should_continue:
                    break

            # Verify state
            assert tracker.total_experiments == 5
            assert tracker.total_tokens > 0
            assert len(tracker.experiment_costs) == 5

    def test_cost_budget_enforcement(self):
        """[COST-15] Hard budget limits enforced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(
                    max_cost_usd=1.0,
                    max_experiments=100,
                    hard_limit=True,
                ),
                log_file=Path(tmpdir) / "costs.jsonl",
            )

            # Simulate exceeding budget
            tracker.total_cost = 1.5  # Over budget

            within, status = tracker.check_budget()
            assert within is False
            assert status["cost_ok"] is False

    def test_soft_budget_allows_overflow(self):
        """[COST-16] Soft budget allows overflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(
                budget=CostBudget(
                    max_cost_usd=1.0,
                    hard_limit=False,  # Soft limit
                ),
                log_file=Path(tmpdir) / "costs.jsonl",
            )

            # Simulate exceeding budget
            tracker.total_cost = 1.5

            within, status = tracker.check_budget()
            assert within is True  # Soft limit allows
            assert status["cost_ok"] is False  # But warns
