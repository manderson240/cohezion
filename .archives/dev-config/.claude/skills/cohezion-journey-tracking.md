---
name: cohezion-journey-tracking
description: Agent journey tracking and request alignment assessment for the Cohezion compound engineering loop. Covers JourneyTracker API (record_state, record_transition, save_checkpoint, rollback), RequestAlignmentAnalyzer (coherence, completeness, constraint satisfaction, drift risk), and alignment anti-patterns. Use when implementing compound features, adding journey tracking, or checking request alignment.
---

# Agent Journey Tracking (Compound Loop Observability)

**Every agent action must be trackable through 12D universe. Required for skill refinement and drift detection.**

### Journey Entry Point
```python
from cohezion.compound.journey_tracker import JourneyTracker

tracker = JourneyTracker()
state_before = tracker.record_state(
    agent_id="researcher-1",
    phase="research",  # {research, planning, execution, reflection}
    position={"x": 0.5, "y": 0.3, ...},  # 12D coordinates
    coherence=0.85,  # Agent's skill coherence
    context=request_state  # Input to this phase
)
```

### Checkpoints (Non-Blocking)
```python
# Record at state transitions (try/except to prevent crashes)
try:
    tracker.record_transition(
        state_before,
        action_taken,
        result,
        coherence_after=0.83,
        alignment_score=0.92  # How well action matched request
    )
except Exception as e:
    logger.warning(f"Journey tracking failed (non-blocking): {e}")
```

### Recovery Checkpoint (Rollback Path)
```python
# Before executing irreversible action, save checkpoint
checkpoint = tracker.save_checkpoint(
    agent_id="researcher-1",
    phase="execution",
    state=current_state
)
# ... execute ...
if failure:
    tracker.rollback_to_checkpoint(checkpoint)
```

### Query Journey (Debugging + Skill Refinement)
```python
# Retrospection engine uses this to refine skills
journey = tracker.get_journey(agent_id="researcher-1")
anomalies = tracker.detect_anomalies(journey)  # Drift, coherence collapse
for anomaly in anomalies:
    logger.info(f"Anomaly: {anomaly.phase} → coherence {anomaly.before} → {anomaly.after}")
```

---

# Request Alignment Assessment (Before Execution)

**Every request must be assessed for alignment with available skills and agent context. Prevents wasted tokens on misaligned tasks.**

### Alignment Analysis Pipeline
```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer
from cohezion.compound.skill_selector import SkillSelector

analyzer = RequestAlignmentAnalyzer()
selector = SkillSelector()

# 1. Parse request and check available skills
request = parse_request(user_input)  # {goal, constraints, context}
available_skills = selector.find_relevant_skills(request.keywords)

# 2. Assess alignment
alignment = analyzer.analyze(
    request=request,
    available_skills=available_skills,
    agent_coherence=agent.coherence_history,  # Historical performance
    computational_budget=5000  # Tokens available
)

# 3. Make routing decision
if alignment.coherence < 0.5:  # HIHO threshold
    logger.warning(f"Low alignment: {alignment.issues}")
    action = "escalate" or "decompose"  # Break into smaller requests
elif alignment.estimated_tokens > budget:
    action = "batch_or_defer"
else:
    action = "proceed"  # Execute with confidence
    selected_skill = alignment.best_matching_skill
```

### Alignment Score Components
- **Coherence** (0.0-1.0): How well request matches agent's expertise
- **Completeness** (0.0-1.0): Are all required params present?
- **Constraint Satisfaction** (0.0-1.0): Can execution honor time/token/resource constraints?
- **Drift Risk** (0.0-1.0): How much could this destabilize coherence?
- **Estimated Tokens**: Projection for cost budgeting

### Anti-Patterns
- ❌ Accept ANY request without alignment check (wastes tokens)
- ❌ Proceed with coherence <0.5 (HIHO collapse)
- ❌ Ignore computational_budget (tokens explode)
- ❌ Skip drift detection (coherence decays)
