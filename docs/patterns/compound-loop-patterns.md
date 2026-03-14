# Compound Loop Patterns Reference

Extracted from CLAUDE.md for on-demand reference. Use `vexor search "journey tracking"` or read this file directly when implementing compound loop features.

## Agent Journey Tracking

Every agent action must be trackable through 12D universe. Required for skill refinement and drift detection.

### Journey Entry Point
```python
from cohezion.compound.journey_tracker import JourneyTracker

tracker = JourneyTracker()
state_before = tracker.record_state(
    agent_id="researcher-1",
    phase="research",  # {research, planning, execution, reflection}
    position={"x": 0.5, "y": 0.3, ...},  # 12D coordinates
    coherence=0.85,
    context=request_state
)
```

### Checkpoints (Non-Blocking)
```python
try:
    tracker.record_transition(
        state_before, action_taken, result,
        coherence_after=0.83, alignment_score=0.92
    )
except Exception as e:
    logger.warning(f"Journey tracking failed (non-blocking): {e}")
```

### Recovery Checkpoint (Rollback Path)
```python
checkpoint = tracker.save_checkpoint(agent_id="researcher-1", phase="execution", state=current_state)
if failure:
    tracker.rollback_to_checkpoint(checkpoint)
```

### Query Journey
```python
journey = tracker.get_journey(agent_id="researcher-1")
anomalies = tracker.detect_anomalies(journey)
```

## Request Alignment Assessment

### Alignment Analysis Pipeline
```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer
from cohezion.compound.skill_selector import SkillSelector

analyzer = RequestAlignmentAnalyzer()
selector = SkillSelector()

request = parse_request(user_input)
available_skills = selector.find_relevant_skills(request.keywords)
alignment = analyzer.analyze(
    request=request,
    available_skills=available_skills,
    agent_coherence=agent.coherence_history,
    computational_budget=5000
)

if alignment.coherence < 0.5:  # HIHO threshold
    action = "escalate" or "decompose"
elif alignment.estimated_tokens > budget:
    action = "batch_or_defer"
else:
    action = "proceed"
    selected_skill = alignment.best_matching_skill
```

### Alignment Score Components
- **Coherence** (0.0-1.0): Request matches agent's expertise
- **Completeness** (0.0-1.0): All required params present
- **Constraint Satisfaction** (0.0-1.0): Can honor time/token/resource constraints
- **Drift Risk** (0.0-1.0): Destabilization potential
- **Estimated Tokens**: Cost projection

## Metrics & Observability

### Recording Metrics
```python
from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator

agg = GlobalMetricsAggregator()
agg.record_execution(
    instance_metrics={
        "executions": 1, "tokens_used": 1250, "coherence": 0.87,
        "cache_hit_rate": 0.95, "cost_usd": 0.002, "latency_ms": 450,
    },
    skill_name="research", agent_id="researcher-1"
)
```

### Querying Metrics
```python
snapshot = agg.get_metrics_snapshot()
skill_metrics = agg.get_skill_metrics("research", days=7)
if skill_metrics.coherence_trend < -0.05:
    logger.warning("research skill coherence degrading, trigger refinement")
```

### Cost Tracking (Budget Enforcement)
```python
from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer

enforcer = BudgetEnforcer(monthly_budget_usd=100)
can_proceed, remaining = enforcer.check_budget(estimated_tokens=5000)
```

## Data Storage Architecture (Three-Tier)

**Problem**: Simulation artifacts accumulate exponentially without governance.

| Tier | Storage | Content | Retention |
|------|---------|---------|-----------|
| 1: Git | Repo | Checksums, configs, hyperparams, seeds (<1MB) | Permanent |
| 2: SurrealDB | Queryable index | Artifact metadata (path, size, checksum, lifetime) | Rolling 100K records |
| 3: External | s3/gdrive/NVMe | Checkpoint weights, large artifacts (>50MB) | Policy-driven 30-90 days |

### Artifact Registration
```python
JourneyTracker.record_artifact(
    session_id="session-55", artifact_type="checkpoint",
    path="data/flume/session55_run3.pt", size_bytes=234_567_890,
    tier="external", checksum="sha256:abcd1234",
    lifetime_days=30, retention_policy="research", tags=["flume", "vae"]
)
```

### Recovery (Deterministic Replay)
```python
checkpoint = CheckpointRepo.get_by_seed(seed=42, session="session-55")
state = torch.load(checkpoint.git_ref)
vae = FlumVAETrainer.from_checkpoint(state, continue_training=True)
```

### Pre-Commit Hook
Block commits with >50MB files without external artifact registration. See `CLAUDE.md` for hook script.

### Success Metrics
| Metric | Target |
|--------|--------|
| Committed files/session | <50 MB |
| Artifact discoverability | <5 ms |
| Recovery time | <5 min |
| Storage cost | <$5/10 sessions |
