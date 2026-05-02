"""Tests for real-time cost monitoring dashboard.

Tests cover:
- Cost aggregation by model, team, and time
- Real-time spend rate calculations
- Budget vs. actual tracking
- Trend data collection and forecasting
- Dashboard API endpoints and data accuracy
"""

import time

import pytest

from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
from cohezion.cost_optimization.cost_dashboard import (
    BudgetStatus,
    CostBreakdown,
    CostDashboard,
    SpendRate,
    TrendPoint,
    get_cost_dashboard,
    reset_cost_dashboard,
)
from cohezion.cost_optimization.cost_tracker import SessionCostTracker


class TestCostBreakdown:
    """Test cost breakdown data structure."""

    def test_cost_breakdown_initialization(self):
        """Test CostBreakdown initialization."""
        breakdown = CostBreakdown(total_cost_usd=10.50)

        assert breakdown.total_cost_usd == 10.50
        assert breakdown.cost_by_model == {}
        assert breakdown.cost_by_team == {}

    def test_cost_breakdown_to_dict(self):
        """Test CostBreakdown serialization to dict."""
        breakdown = CostBreakdown(
            total_cost_usd=5.0,
            cost_by_model={"phi3:mini": 2.0, "qwen3": 3.0},
        )

        data = breakdown.to_dict()
        assert data["total_cost_usd"] == 5.0
        assert data["cost_by_model"]["phi3:mini"] == 2.0


class TestSpendRate:
    """Test spend rate calculations."""

    def test_spend_rate_initialization(self):
        """Test SpendRate initialization."""
        rate = SpendRate(
            spend_per_minute_usd=0.1,
            spend_per_hour_usd=6.0,
            spend_per_day_usd=144.0,  # Explicitly set
        )

        assert rate.spend_per_minute_usd == 0.1
        assert rate.spend_per_hour_usd == 6.0
        assert rate.spend_per_day_usd == 144.0

    def test_spend_rate_trend_direction(self):
        """Test trend direction assignment."""
        rate = SpendRate(
            spend_per_minute_usd=0.1,
            trend_direction="increasing",
        )

        assert rate.trend_direction == "increasing"


class TestBudgetStatus:
    """Test budget status tracking."""

    def test_budget_status_healthy(self):
        """Test healthy budget status."""
        status = BudgetStatus(
            total_budget_usd=100.0,
            total_spent_usd=30.0,
            remaining_budget_usd=70.0,
            budget_utilization_pct=30.0,
            budget_status="healthy",
        )

        assert status.budget_utilization_pct == 30.0
        assert status.budget_status == "healthy"
        assert status.alert_level == "none"

    def test_budget_status_warning(self):
        """Test warning budget status."""
        status = BudgetStatus(
            total_budget_usd=100.0,
            total_spent_usd=85.0,
            remaining_budget_usd=15.0,
            budget_utilization_pct=85.0,
            budget_status="warning",
            alert_level="warning",
        )

        assert status.budget_status == "warning"
        assert status.alert_level == "warning"

    def test_budget_status_critical(self):
        """Test critical budget status."""
        status = BudgetStatus(
            total_budget_usd=100.0,
            total_spent_usd=100.0,
            remaining_budget_usd=0.0,
            budget_utilization_pct=100.0,
            budget_status="critical",
            alert_level="critical",
        )

        assert status.budget_status == "critical"
        assert status.alert_level == "critical"


class TestCostDashboard:
    """Test cost dashboard functionality."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard with mock dependencies."""
        reset_cost_dashboard()
        tracker = SessionCostTracker("test-dashboard")
        enforcer = BudgetEnforcer(budget_usd=100.0)
        dashboard = CostDashboard(
            cost_tracker=tracker,
            budget_enforcer=enforcer,
        )
        return dashboard

    def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard.cost_tracker is not None
        assert dashboard.budget_enforcer is not None
        assert dashboard.history_window_hours == 24

    def test_get_cost_breakdown(self, dashboard):
        """Test cost breakdown retrieval."""
        breakdown = dashboard.get_cost_breakdown()

        assert isinstance(breakdown, CostBreakdown)
        assert breakdown.total_cost_usd >= 0.0

    def test_get_spend_rate(self, dashboard):
        """Test spend rate calculation."""
        # Simulate some time passing
        time.sleep(0.1)

        rate = dashboard.get_spend_rate()

        assert isinstance(rate, SpendRate)
        assert rate.spend_per_hour_usd >= 0.0
        assert rate.spend_per_day_usd >= 0.0

    def test_get_budget_status(self, dashboard):
        """Test budget status tracking."""
        status = dashboard.get_budget_status()

        assert isinstance(status, BudgetStatus)
        assert status.total_budget_usd == 100.0
        assert 0.0 <= status.budget_utilization_pct <= 100.0

    def test_get_weekly_trend(self, dashboard):
        """Test weekly trend data retrieval."""
        # Add some trend points
        dashboard.update_trend_history()
        time.sleep(0.01)
        dashboard.update_trend_history()

        trend = dashboard.get_weekly_trend()

        assert isinstance(trend, list)
        assert len(trend) >= 1

    def test_update_trend_history(self, dashboard):
        """Test trend history update."""
        initial_count = len(dashboard.trend_history)

        dashboard.update_trend_history()

        assert len(dashboard.trend_history) == initial_count + 1

    def test_trend_point_creation(self, dashboard):
        """Test trend point creation with metrics."""
        dashboard.update_trend_history()

        if dashboard.trend_history:
            point = dashboard.trend_history[-1]
            assert isinstance(point, TrendPoint)
            assert point.timestamp > 0
            assert point.cost_usd >= 0.0

    def test_get_cost_by_model_pie_chart(self, dashboard):
        """Test pie chart data generation."""
        # Mock some cost by model
        dashboard.cost_tracker.model_costs = {
            "phi3:mini": 1.0,
            "qwen3": 2.0,
        }

        # Manually set breakdown
        breakdown = dashboard.get_cost_breakdown()
        breakdown.cost_by_model = {
            "phi3:mini": 1.0,
            "qwen3": 2.0,
        }
        breakdown.total_cost_usd = 3.0

        # We'd need to override to test fully - for now just verify structure
        pie_chart = dashboard.get_cost_by_model_pie_chart()

        assert isinstance(pie_chart, dict)

    def test_get_cost_forecasts(self, dashboard):
        """Test cost forecasting."""
        forecasts = dashboard.get_cost_forecasts(forecast_hours=24)

        assert isinstance(forecasts, dict)
        # Should have forecast keys for hours 1-24
        assert len(forecasts) == 24

    def test_get_dashboard_summary(self, dashboard):
        """Test complete dashboard summary."""
        summary = dashboard.get_dashboard_summary()

        assert isinstance(summary, dict)
        assert "timestamp" in summary
        assert "cost_breakdown" in summary
        assert "spend_rate" in summary
        assert "budget_status" in summary
        assert "cost_by_model_pie" in summary
        assert "weekly_trend" in summary
        assert "forecasts" in summary

    def test_dashboard_summary_structure(self, dashboard):
        """Test dashboard summary has correct structure."""
        summary = dashboard.get_dashboard_summary()

        # Verify cost_breakdown structure
        breakdown = summary["cost_breakdown"]
        assert "total_cost_usd" in breakdown
        assert "cost_by_model" in breakdown

        # Verify spend_rate structure
        spend = summary["spend_rate"]
        assert "spend_per_minute_usd" in spend
        assert "spend_per_hour_usd" in spend

        # Verify budget_status structure
        budget = summary["budget_status"]
        assert "total_budget_usd" in budget
        assert "budget_status" in budget


class TestCostDashboardQueries:
    """Test dashboard query performance."""

    @pytest.fixture
    def dashboard_with_history(self):
        """Create dashboard with historical data."""
        reset_cost_dashboard()
        tracker = SessionCostTracker("test-history")
        enforcer = BudgetEnforcer(budget_usd=100.0)
        dashboard = CostDashboard(
            cost_tracker=tracker,
            budget_enforcer=enforcer,
        )

        # Add historical trend points
        for i in range(10):
            dashboard.trend_history.append(
                TrendPoint(
                    timestamp=time.time() - (10 - i) * 3600,  # 10 hours ago to now
                    cost_usd=1.0 + (i * 0.1),
                    tokens=100 + (i * 10),
                    execution_count=10 + i,
                )
            )

        return dashboard

    def test_query_latency_under_100ms(self, dashboard_with_history):
        """Test dashboard queries complete within 100ms."""
        start = time.time()

        # Execute various queries
        dashboard_with_history.get_cost_breakdown()
        dashboard_with_history.get_spend_rate()
        dashboard_with_history.get_budget_status()
        dashboard_with_history.get_weekly_trend()
        dashboard_with_history.get_dashboard_summary()

        elapsed_ms = (time.time() - start) * 1000

        # All queries should complete in <100ms
        assert elapsed_ms < 100.0

    def test_weekly_trend_filtering(self, dashboard_with_history):
        """Test weekly trend correctly filters data."""
        trend = dashboard_with_history.get_weekly_trend()

        # With 10 data points from 10 hours ago, all should be in 7-day window
        assert len(trend) >= 10

    def test_cost_breakdown_aggregation(self, dashboard_with_history):
        """Test cost breakdown aggregates correctly."""
        breakdown = dashboard_with_history.get_cost_breakdown()

        assert isinstance(breakdown, CostBreakdown)
        assert breakdown.total_cost_usd >= 0.0


class TestCostDashboardIntegration:
    """Integration tests with CostTracker and BudgetEnforcer."""

    def test_dashboard_with_budget_enforcer(self):
        """Test dashboard integration with BudgetEnforcer."""
        reset_cost_dashboard()
        tracker = SessionCostTracker("integration-test")
        enforcer = BudgetEnforcer(budget_usd=50.0)

        dashboard = CostDashboard(
            cost_tracker=tracker,
            budget_enforcer=enforcer,
        )

        status = dashboard.get_budget_status()

        assert status.total_budget_usd == 50.0
        assert status.budget_status in ["healthy", "warning", "critical"]

    def test_dashboard_alerts_on_high_utilization(self):
        """Test dashboard alerts when utilization is high."""
        reset_cost_dashboard()
        tracker = SessionCostTracker("alert-test")
        tracker.total_cost_usd = 85.0  # Simulate high cost

        enforcer = BudgetEnforcer(budget_usd=100.0)

        dashboard = CostDashboard(
            cost_tracker=tracker,
            budget_enforcer=enforcer,
        )

        status = dashboard.get_budget_status()

        assert status.budget_utilization_pct >= 80.0
        assert status.alert_level == "warning"

    def test_singleton_pattern(self):
        """Test dashboard singleton pattern."""
        reset_cost_dashboard()

        dashboard1 = get_cost_dashboard()
        dashboard2 = get_cost_dashboard()

        assert dashboard1 is dashboard2

    def test_reset_singleton(self):
        """Test singleton reset."""
        dashboard1 = get_cost_dashboard()

        reset_cost_dashboard()

        dashboard2 = get_cost_dashboard()

        assert dashboard1 is not dashboard2
