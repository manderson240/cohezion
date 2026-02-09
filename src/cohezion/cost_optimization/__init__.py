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

__all__ = [
    "SessionCostTracker",
    "CostRecord",
    "BudgetEnforcer",
    "BudgetPolicy",
    "CostAwareRouter",
    "CostDashboard",
]
