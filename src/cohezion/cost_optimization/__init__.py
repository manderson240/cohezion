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

import contextlib


with contextlib.suppress(Exception):
    from cohezion.cost_optimization.budget_enforcer import (
        BudgetCircuitBreaker as BudgetCircuitBreaker,
    )
    from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer as BudgetEnforcer
    from cohezion.cost_optimization.budget_enforcer import BudgetPolicy as BudgetPolicy
    from cohezion.cost_optimization.budget_enforcer import BudgetState as BudgetState
    from cohezion.cost_optimization.budget_enforcer import CostAlertManager as CostAlertManager
    from cohezion.cost_optimization.budget_enforcer import (
        get_current_enforcer as get_current_enforcer,
    )
    from cohezion.cost_optimization.budget_enforcer import (
        reset_current_enforcer as reset_current_enforcer,
    )
    from cohezion.cost_optimization.budget_enforcer import (
        set_current_enforcer as set_current_enforcer,
    )

with contextlib.suppress(Exception):
    from cohezion.cost_optimization.cost_tracker import CostRecord as CostRecord
    from cohezion.cost_optimization.cost_tracker import SessionCostTracker as SessionCostTracker
    from cohezion.cost_optimization.cost_tracker import get_current_tracker as get_current_tracker
    from cohezion.cost_optimization.cost_tracker import (
        reset_current_tracker as reset_current_tracker,
    )
    from cohezion.cost_optimization.cost_tracker import set_current_tracker as set_current_tracker

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
    "CostAlertManager",
    "CostRecord",
    "Forecast",
    "ForecastEngine",
    "ForecastSummary",
    "SessionCostTracker",
    "get_current_enforcer",
    "get_current_tracker",
    "get_forecast_engine",
    "reset_current_enforcer",
    "reset_current_tracker",
    "reset_forecast_engine",
    "set_current_enforcer",
    "set_current_tracker",
]

with contextlib.suppress(Exception):
    from cohezion.cost_optimization.cost_dashboard import BudgetStatus as BudgetStatus
    from cohezion.cost_optimization.cost_dashboard import CostBreakdown as CostBreakdown
    from cohezion.cost_optimization.cost_dashboard import SpendRate as SpendRate

with contextlib.suppress(Exception):
    from cohezion.cost_optimization.forecast_engine import Forecast as Forecast
    from cohezion.cost_optimization.forecast_engine import ForecastEngine as ForecastEngine
    from cohezion.cost_optimization.forecast_engine import ForecastSummary as ForecastSummary
