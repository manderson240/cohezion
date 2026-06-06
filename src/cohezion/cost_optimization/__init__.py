"""Cost optimization infrastructure for the Cohezion framework.

Provides:
- Cost tracking with minimal overhead (<0.05ms per call)
- Budget enforcement with soft-stop policy
- Cost-aware model routing with cache affinity
- Real-time cost monitoring and analytics
- Immutable audit trails

Architecture:
1. Tracking: SessionCostTracker (in-memory) + batched async flush
2. Enforcement: BudgetEnforcer (cached checks, 60s refresh)
3. Optimization: CostAwareRouter (cache-affinity variant)
4. Observability: Cost dashboard + vault analytics
"""

from cohezion.cost_optimization.budget_enforcer import (
    BudgetCircuitBreaker,
    BudgetEnforcer,
    BudgetPolicy,
    BudgetState,
    CostAlertManager,
    get_current_enforcer,
    reset_current_enforcer,
    set_current_enforcer,
)

# Wiring-sweep (2026-06-06): cost_dashboard was a genuine Class-A orphan (0 production importers —
# only a test edge), though its siblings above were already re-exported. Added to the public surface
# (observability layer, per the module docstring) so it is reachable via a literal static edge.
from cohezion.cost_optimization.cost_dashboard import (
    BudgetStatus,
    CostBreakdown,
    CostDashboard,
    SpendRate,
    TrendPoint,
    get_cost_dashboard,
)
from cohezion.cost_optimization.cost_tracker import (
    CostRecord,
    SessionCostTracker,
    get_current_tracker,
    reset_current_tracker,
    set_current_tracker,
)

# Wiring-sweep (2026-06-06): forecast_engine — the last cost_optimization/ Class-A orphan (0
# production importers, only a test edge). Re-exported here, completing the package's public surface.
from cohezion.cost_optimization.forecast_engine import (
    AnomalyScore,
    Forecast,
    ForecastEngine,
    ForecastSummary,
    get_forecast_engine,
    reset_forecast_engine,
)


__all__ = [
    "AnomalyScore",
    "BudgetCircuitBreaker",
    "BudgetEnforcer",
    "BudgetPolicy",
    "BudgetState",
    "BudgetStatus",
    "CostAlertManager",
    "CostBreakdown",
    "CostDashboard",
    "CostRecord",
    "Forecast",
    "ForecastEngine",
    "ForecastSummary",
    "SessionCostTracker",
    "SpendRate",
    "TrendPoint",
    "get_cost_dashboard",
    "get_current_enforcer",
    "get_current_tracker",
    "get_forecast_engine",
    "reset_current_enforcer",
    "reset_current_tracker",
    "reset_forecast_engine",
    "set_current_enforcer",
    "set_current_tracker",
]
