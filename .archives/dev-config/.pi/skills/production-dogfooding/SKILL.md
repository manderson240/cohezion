---
name: production-dogfooding
description: 4-phase framework for validating systems through real-world use with metrics-driven decisions and self-improvement loops.
---

# Production Dogfooding Framework

Complete framework for validating systems through real-world use. Includes 4 phases: tool usage, metrics-driven decisions, self-improvement, and production hardening.

## When to Use

Use for any system that needs production validation:
- ✅ New frameworks/tools
- ✅ System rewrites
- ✅ Optimization projects
- ✅ Production readiness validation

## The 4 Phases

### Phase 1: Use Your Own Tools

**Goal**: 100% of work uses your systems

**Checklist**:
- [ ] Use V-Model for all changes
- [ ] Session management via CompoundSessionManager
- [ ] Testing via Multi-Agent system

**Success Metrics**:
- Adjustments via V-Model: 100%
- Session manager usage: 100%
- Tests via multi-agent: >50%

**Example**:
```python
from cohezion.swarm.dynamic_levers import create_default_lever_system
from cohezion.swarm.vmodel_engineering import VModelIntegratedLeverSystem

lever_system = create_default_lever_system()
vmodel = VModelIntegratedLeverSystem(lever_system)

requirements = {
    "goal": "Clear statement of what we're achieving",
    "target_value": 0.50,
    "justification": "Why this change is needed",
    "constraints": ["must_be_positive", "backward_compatible"],
    "acceptance_criteria": {"metric": 0.50}
}

adj_id = vmodel.adjust_lever_vmodel(
    lever_name="deterministic_ratio",
    target_value=0.50,
    requirements=requirements
)
```

---

### Phase 2: Metrics Drive Decisions

**Goal**: Dashboard becomes primary interface

**Daily Workflow**:
```
Morning (9:00 AM):
  1. Run daily cycle
  2. Review dashboard
  3. Identify priorities
  4. Set session goals

During Work:
  1. Check dashboard before changes
  2. Data-driven decisions only
  3. Document metric deviations

Evening (5:00 PM):
  1. Review goal progress
  2. Document learnings
  3. Log to SurrealDB
```

**Success Metrics**:
- Dashboard-driven decisions: >80%
- Auto-adjustments: >50%
- Cross-session learnings: >3/month

---

### Phase 3: Self-Improvement Loop

**Goal**: Systems improve from usage

**Components**:

#### Auto-Improving Parser
```python
from cohezion.swarm.auto_improving_parser import AutoImprovingParser

parser = AutoImprovingParser()

# Run weekly cycle
result = parser.run_improvement_cycle(test_data)

# Review learned patterns
for pattern in parser.learner.get_pending_review():
    # Human review
    if approve(pattern):
        parser.learner.approve_pattern(pattern)
```

#### Phase Optimizer
```python
from cohezion.swarm.vmodel_phase_optimizer import PhaseOptimizer

optimizer = PhaseOptimizer()

# Analyze bottlenecks
bottlenecks = optimizer.analyze_bottlenecks()

# Get optimization plan
plan = optimizer.get_optimization_plan()
if plan["status"] == "optimization_recommended"]:
    implement_optimization(plan)
```

#### Predictive Adjuster
```python
from cohezion.swarm.predictive_lever_adjuster import PredictiveLeverAdjuster

adjuster = PredictiveLeverAdjuster(lever_system)

# Make prediction
request = adjuster.predict_and_execute("deterministic_ratio")

# Check if actionable
if request and request.prediction.is_actionable(0.75):
    # Execute or queue for approval
    pass
```

**Success Metrics**:
- Auto-parser updates: 10%
- Phase time reduction: 20%
- Predictive adjustments: 1/week

---

### Phase 4: Production Hardening

**Goal**: 99.9% reliability

**CI/CD Integration**:
```bash
# Install pre-commit hook
python -m cohezion.dogfooding.production_hardening --install-hook

# Check compliance
python -m cohezion.dogfooding.production_hardening --check
```

**Performance Monitoring**:
```python
from cohezion.dogfooding.production_hardening import PerformanceMonitor

monitor = PerformanceMonitor()

# Record metrics
monitor.record_metric("dashboard_load_ms", 0.2)

# Check alerts
alerts = monitor.check_alerts()
for alert in alerts:
    notify(alert)
```

**Disaster Recovery**:
```python
from cohezion.dogfooding.production_hardening import DisasterRecovery

dr = DisasterRecovery()

# Create checkpoint
checkpoint_id = dr.create_checkpoint(lever_system)

# Restore if needed
success = dr.restore_checkpoint(checkpoint_id, lever_system)
```

**Success Metrics**:
- V-Model compliance: 100%
- Metric latency: <5s
- Recovery time: <5min

---

## Daily Cycle Automation

```python
from cohezion.dogfooding import DailyDogfoodingCycle

cycle = DailyDogfoodingCycle()

# Run daily
results = await cycle.run_daily_cycle()

# Results include:
# - Dashboard review summary
# - Predictive adjustments
# - Auto-improvement cycle
# - Phase optimization analysis
# - Logged to disk
```

**Cron Schedule**:
```cron
# Daily at 9:00 AM
0 9 * * * cd /path/to/cohezion && \
  uv run python -m cohezion.dogfooding.daily_cycle

# Hourly hardening check
0 * * * * cd /path/to/cohezion && \
  uv run python -m cohezion.dogfooding.production_hardening
```

---

## Key Learnings

### 1. Dogfooding Validates Design
Using your own tools reveals issues specs miss.

### 2. Metrics Enable Decisions
Dashboard data drives prioritization.

### 3. Human-in-the-Loop Required
Automation without oversight risks errors.

### 4. Phase-Based Approach Works
Clear milestones ensure completion.

### 5. Production Needs All Three
Function + Monitoring + Recovery = 99.9%

---

## Common Pitfalls

### ❌ Don't Skip Phase 1
Trying to automate before using tools manually.

### ❌ Don't Automate Too Fast
High automation without safety controls.

### ❌ Don't Skip Human Review
Auto-approve thresholds too low.

### ❌ Don't Ignore Dashboard
Making decisions without data.

### ❌ Perfectionism
Waiting for perfect before deploying.

---

## Best Practices

### ✅ Start Simple
Manual usage before automation.

### ✅ Measure Everything
Dashboard tracks all metrics.

### ✅ Safety First
Rollback plans before changes.

### ✅ Iterate
Progressive hardening over time.

### ✅ Document
Capture learnings in real-time.

---

## Files

```
cohezion/dogfooding/
├── __init__.py                  Package exports
├── daily_cycle.py               5-step automation
└── production_hardening.py      CI/CD, monitoring, DR

cohezion/swarm/
├── auto_improving_parser.py     Pattern learning
├── vmodel_phase_optimizer.py    Optimization
└── predictive_lever_adjuster.py Predictions
```

---

## Example: Complete Session

```python
# 1. Initialize
from cohezion.dogfooding import DailyDogfoodingCycle

cycle = DailyDogfoodingCycle()

# 2. Run cycle
results = await cycle.run_daily_cycle()

# 3. Review results
print(f"Dashboard: {results['steps']['dashboard_review']['goals_achieved']} goals")
print(f"Predictions: {results['steps']['predictive_adjustments']['executed']} executed")
print(f"Improvements: {results['steps']['auto_improvement']['patterns_learned']} patterns")

# 4. Check health
from cohezion.dogfooding import ProductionHardening
hardening = ProductionHardening()
health = await hardening.run_hardening_check(cycle.lever_system)

print(f"Health: {health['health']['status']}")
```

---

**Version**: 1.0  
**Scope**: Complete 4-phase dogfooding framework  
**Status**: Production-ready
