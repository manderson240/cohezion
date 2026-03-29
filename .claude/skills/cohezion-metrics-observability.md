---
name: cohezion-metrics-observability
description: Production monitoring and metrics for the Cohezion compound engineering system. Covers GlobalMetricsAggregator (recording executions, querying snapshots, skill trends), BudgetEnforcer (monthly budget checks, token budget control), and cost tracking. Use when implementing metrics, monitoring costs, or debugging budget issues.
---

# Metrics & Observability (Production Monitoring)

**Global metrics track efficiency, cost, and quality across all agents and executions.**

### Recording Metrics
```python
from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator

agg = GlobalMetricsAggregator()

# Record after each execution
agg.record_execution(
    instance_metrics={
        "executions": 1,
        "tokens_used": 1250,
        "coherence": 0.87,
        "cache_hit_rate": 0.95,
        "cost_usd": 0.002,
        "latency_ms": 450,
    },
    skill_name="research",
    agent_id="researcher-1"
)
```

### Querying Metrics (Dashboards + Analysis)
```python
# Real-time dashboard (5-min rolling window)
snapshot = agg.get_metrics_snapshot()
print(f"Throughput: {snapshot.avg_tokens_per_sec} tokens/sec")
print(f"Cache hit: {snapshot.cache_hit_rate:.1%}")
print(f"Cost trending: ${snapshot.daily_cost_estimate:.2f}")

# Historical trends (skill refinement)
skill_metrics = agg.get_skill_metrics("research", days=7)
if skill_metrics.coherence_trend < -0.05:  # Degrading
    logger.warning("research skill coherence degrading, trigger refinement")
```

### Cost Tracking (Budget Enforcement)
```python
from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer

enforcer = BudgetEnforcer(monthly_budget_usd=100)

# Check before execution
can_proceed, remaining = enforcer.check_budget(estimated_tokens=5000)
if not can_proceed:
    logger.info(f"Budget exhausted, {remaining} tokens remain for month")
    action = "defer_or_escalate"
```
