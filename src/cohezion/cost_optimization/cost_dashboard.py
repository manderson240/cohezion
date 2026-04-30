"""Real-time cost monitoring dashboard for multi-agent teams.

Provides dashboard APIs for:
- Cost aggregation by model, team, time window
- Real-time spend rate ($/minute, $/hour)
- Budget vs. actual tracking with alerts
- Cost breakdown visualization (pie chart)
- Weekly trend graphs
- Integration with GlobalMetricsAggregator and BudgetEnforcer
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, TYPE_CHECKING

from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
from cohezion.cost_optimization.cost_tracker import SessionCostTracker

if TYPE_CHECKING:
    from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator


logger = logging.getLogger(__name__)


@dataclass
class CostBreakdown:
    """Cost breakdown by dimension (model, team, time)."""

    total_cost_usd: float = 0.0
    cost_by_model: dict[str, float] = field(default_factory=dict)
    cost_by_team: dict[str, float] = field(default_factory=dict)
    cost_by_hour: dict[str, float] = field(default_factory=dict)
    tokens_by_model: dict[str, int] = field(default_factory=dict)
    executions_by_model: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SpendRate:
    """Real-time spend rate metrics."""

    timestamp: float = field(default_factory=time.time)
    spend_per_minute_usd: float = 0.0
    spend_per_hour_usd: float = 0.0
    spend_per_day_usd: float = 0.0
    current_rate_slope: float = 0.0  # USD/minute trend
    trend_direction: str = "stable"  # "increasing", "decreasing", "stable"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BudgetStatus:
    """Budget vs actual tracking."""

    timestamp: float = field(default_factory=time.time)
    total_budget_usd: float = 0.0
    total_spent_usd: float = 0.0
    remaining_budget_usd: float = 0.0
    budget_utilization_pct: float = 0.0
    budget_status: str = "healthy"  # "healthy", "warning", "critical"
    hours_remaining_at_current_rate: float = 0.0
    alert_level: str = "none"  # "none", "warning", "critical"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrendPoint:
    """Single data point for trend graphs."""

    timestamp: float
    cost_usd: float
    tokens: int
    execution_count: int
    avg_cost_per_execution: float = 0.0


class CostDashboard:
    """Real-time cost monitoring dashboard."""

    def __init__(
        self,
        cost_tracker: SessionCostTracker | None = None,
        budget_enforcer: BudgetEnforcer | None = None,
        metrics_aggregator: GlobalMetricsAggregator | None = None,
        history_window_hours: int = 24,
    ):
        """Initialize cost dashboard.

        Args:
            cost_tracker: SessionCostTracker instance (optional)
            budget_enforcer: BudgetEnforcer instance (optional)
            metrics_aggregator: GlobalMetricsAggregator instance (optional)
            history_window_hours: Hours of history to track (default: 24)
        """
        self.cost_tracker = cost_tracker or SessionCostTracker.get_current()
        self.budget_enforcer = budget_enforcer or BudgetEnforcer.get_current()
        self.metrics_aggregator = metrics_aggregator

        self.history_window_hours = history_window_hours
        self.history_start_time = time.time()

        # Trend history: list of (timestamp, cost, tokens, executions)
        self.trend_history: list[TrendPoint] = []
        self.last_aggregation_time = time.time()

    def get_cost_breakdown(self, time_window_minutes: int = 60) -> CostBreakdown:
        """Get cost breakdown by model, team, time window.

        Args:
            time_window_minutes: Time window for aggregation (default: 60 min)

        Returns:
            CostBreakdown with costs and tokens by dimension
        """
        if not self.cost_tracker:
            return CostBreakdown()

        # Get current session cost info
        session_cost = self.cost_tracker.get_session_cost()

        breakdown = CostBreakdown(
            total_cost_usd=session_cost.get("total_cost_usd", 0.0),
        )

        # Aggregate by model from tracker history if available
        if hasattr(self.cost_tracker, "model_costs"):
            for model, cost in self.cost_tracker.model_costs.items():
                breakdown.cost_by_model[model] = cost

        if hasattr(self.cost_tracker, "token_count"):
            breakdown.tokens_by_model["all_models"] = session_cost.get("total_tokens", 0)

        return breakdown

    def get_spend_rate(self) -> SpendRate:
        """Get real-time spend rate metrics.

        Returns:
            SpendRate with current spend rates and trend
        """
        if not self.cost_tracker:
            return SpendRate()

        session_cost = self.cost_tracker.get_session_cost()
        elapsed_minutes = max(1, (time.time() - self.history_start_time) / 60)

        total_spent = session_cost.get("total_cost_usd", 0.0)
        spend_per_minute = total_spent / elapsed_minutes if elapsed_minutes > 0 else 0.0

        # Calculate trend from recent history
        trend_direction = "stable"
        if len(self.trend_history) >= 2:
            recent = self.trend_history[-1]
            previous = self.trend_history[-2] if len(self.trend_history) > 1 else None
            if previous:
                cost_change = recent.cost_usd - previous.cost_usd
                if cost_change > 0.01:
                    trend_direction = "increasing"
                elif cost_change < -0.01:
                    trend_direction = "decreasing"

        return SpendRate(
            spend_per_minute_usd=spend_per_minute,
            spend_per_hour_usd=spend_per_minute * 60,
            spend_per_day_usd=spend_per_minute * 60 * 24,
            trend_direction=trend_direction,
        )

    def get_budget_status(self) -> BudgetStatus:
        """Get budget vs actual tracking.

        Returns:
            BudgetStatus with budget tracking and alerts
        """
        if not self.budget_enforcer or not self.cost_tracker:
            return BudgetStatus()

        budget_usd = self.budget_enforcer.budget_usd
        spent_usd = self.cost_tracker.total_cost_usd

        utilization_pct = (spent_usd / budget_usd * 100) if budget_usd > 0 else 0

        # Determine budget status
        if utilization_pct >= 100:
            budget_status = "critical"
            alert_level = "critical"
        elif utilization_pct >= 80:
            budget_status = "warning"
            alert_level = "warning"
        else:
            budget_status = "healthy"
            alert_level = "none"

        # Calculate hours remaining at current rate
        spend_rate = self.get_spend_rate()
        remaining_budget = max(0, budget_usd - spent_usd)
        hours_remaining = (
            remaining_budget / spend_rate.spend_per_hour_usd
            if spend_rate.spend_per_hour_usd > 0
            else float("inf")
        )

        return BudgetStatus(
            total_budget_usd=budget_usd,
            total_spent_usd=spent_usd,
            remaining_budget_usd=remaining_budget,
            budget_utilization_pct=utilization_pct,
            budget_status=budget_status,
            hours_remaining_at_current_rate=hours_remaining,
            alert_level=alert_level,
        )

    def get_weekly_trend(self) -> list[TrendPoint]:
        """Get weekly trend data for visualization.

        Returns:
            List of TrendPoint objects for trend graph
        """
        # Return trend history limited to 7 days
        cutoff_time = time.time() - (7 * 24 * 60 * 60)
        return [t for t in self.trend_history if t.timestamp >= cutoff_time]

    def update_trend_history(self) -> None:
        """Update trend history with current metrics.

        Called periodically to record metrics for trend graphs.
        """
        if not self.cost_tracker:
            return

        session_cost = self.cost_tracker.get_session_cost()

        point = TrendPoint(
            timestamp=time.time(),
            cost_usd=session_cost.get("total_cost_usd", 0.0),
            tokens=session_cost.get("total_tokens", 0),
            execution_count=getattr(self.cost_tracker, "execution_count", 0),
        )

        # Calculate average cost per execution
        if point.execution_count > 0:
            point.avg_cost_per_execution = point.cost_usd / point.execution_count

        self.trend_history.append(point)

        # Keep only recent history
        cutoff_time = time.time() - (self.history_window_hours * 60 * 60)
        self.trend_history = [t for t in self.trend_history if t.timestamp >= cutoff_time]

    def get_cost_by_model_pie_chart(self) -> dict[str, float]:
        """Get cost distribution by model for pie chart visualization.

        Returns:
            Dictionary of model -> percentage cost share
        """
        breakdown = self.get_cost_breakdown()

        if not breakdown.cost_by_model or breakdown.total_cost_usd == 0:
            return {}

        pie_data = {}
        for model, cost in breakdown.cost_by_model.items():
            percentage = (cost / breakdown.total_cost_usd) * 100
            pie_data[model] = percentage

        return pie_data

    def get_cost_forecasts(self, forecast_hours: int = 24) -> dict[str, float]:
        """Get cost forecasts for next N hours.

        Args:
            forecast_hours: Hours to forecast (default: 24)

        Returns:
            Dictionary with forecast data
        """
        spend_rate = self.get_spend_rate()
        budget_status = self.get_budget_status()

        forecasts = {}
        current_cost = budget_status.total_spent_usd

        for hour in range(1, forecast_hours + 1):
            projected_cost = current_cost + (spend_rate.spend_per_hour_usd * hour)
            forecasts[f"hour_{hour}"] = projected_cost

        return forecasts

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Get complete dashboard summary for UI rendering.

        Returns:
            Dictionary with all dashboard metrics
        """
        # Update trends
        self.update_trend_history()

        breakdown = self.get_cost_breakdown()
        spend_rate = self.get_spend_rate()
        budget_status = self.get_budget_status()
        pie_chart = self.get_cost_by_model_pie_chart()
        weekly_trend = self.get_weekly_trend()
        forecasts = self.get_cost_forecasts()

        return {
            "timestamp": time.time(),
            "cost_breakdown": breakdown.to_dict(),
            "spend_rate": spend_rate.to_dict(),
            "budget_status": budget_status.to_dict(),
            "cost_by_model_pie": pie_chart,
            "weekly_trend": [
                {
                    "timestamp": t.timestamp,
                    "cost_usd": t.cost_usd,
                    "tokens": t.tokens,
                    "executions": t.execution_count,
                    "avg_cost_per_execution": t.avg_cost_per_execution,
                }
                for t in weekly_trend
            ],
            "forecasts": forecasts,
        }


def get_cost_dashboard() -> CostDashboard:
    """Get or create singleton cost dashboard instance."""
    if not hasattr(get_cost_dashboard, "_instance"):
        get_cost_dashboard._instance = CostDashboard()
    return get_cost_dashboard._instance


def reset_cost_dashboard() -> None:
    """Reset dashboard singleton (testing only)."""
    if hasattr(get_cost_dashboard, "_instance"):
        delattr(get_cost_dashboard, "_instance")
