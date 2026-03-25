# Phase 6: EvalPipeline + Long-Running Claude Patterns

## Overview

Phase 6 implements evaluation pipeline orchestration with RalphLoop, a FOR-loop pattern with DONE incantation and escalation for long-running AI agent evaluation sessions.

## Architecture

```
EvalPipeline
├── RalphLoop (iteration control)
│   ├── DONE incantation detection
│   ├── Escalation (harder variants after failures)
│   └── max_iterations boundary
├── IsolationManager (sandbox via cohezion.sandbox.isolation)
├── Git commits (every 10 successful episodes)
└── EVAL_PROGRESS.md (lab notes)
```

## Key Components

### RalphLoop

RalphLoop implements the "Continue until success criteria met with DONE" pattern:

```python
RalphLoop("Continue until DONE", max_iterations=20)
```

**Behavior:**
1. Each iteration checks for DONE keyword in agent output
2. After `escalation_threshold` failures, difficulty increases
3. Max iterations prevents infinite loops

**Configuration:**
- `done_keyword`: Keyword signaling success (default: "DONE")
- `max_iterations`: Hard stop (default: 20)
- `escalation_threshold`: Failures before escalating (default: 3)
- `escalation_factor`: Difficulty multiplier on escalation (default: 1.5)

### EvalPipeline

Orchestrates episode collection with RalphLoop:

```python
pipeline = EvalPipeline(
    isolation_manager=isolation_manager,  # Sandbox via IsolationManager
    progress_path=Path("data/eval/EVAL_PROGRESS.md"),
    git_auto_commit=True,  # Commit every 10 successful episodes
)

results = pipeline.run(task_spec=task_spec, n_episodes=10)
```

**Integration Points:**
- `TaskGenerator.generate_all()` → TaskSpecs
- `FlumeNavEnv.reset(task_spec)` → EVO environment
- `PPOTrainer` → Policy checkpointing
- `AgenticMetrics.compute()` → Benchmark results

### EVAL_PROGRESS.md

Lab notes format for tracking evaluation progress:

```markdown
# EVAL_PROGRESS.md - Lab Notes

**Updated**: 2026-03-25T12:00:00

## Summary
- **Total Episodes**: 42
- **Successful**: 35
- **Failed**: 5
- **Escalated**: 2
- **Success Rate**: 83.3%

## Milestones
- First interruption_recovery success (episode 12)
- TRIUNE balance mastery (episode 28)

## Failed Approaches
- interruption_recovery (difficulty=1): 7 iterations
- kordylewski_orbit (difficulty=2): 15 iterations

## EVO Physics Tables

### Coherence Dynamics
| Episode | Coherence | Phase | Amplitude |
|---------|-----------|-------|-----------|

### TRIUNE Balance
| Episode | Doer | Thinker | Knower |
|---------|------|---------|--------|
```

## Ralph Loop Pattern

```
FOR iteration IN 1..max_iterations:
    output = execute_agent(task)
    
    IF contains_DONE(output):
        record_success()
        RETURN SUCCESS
    
    record_failure()
    
    IF consecutive_failures >= escalation_threshold:
        increase_difficulty()
        reset_failures()

RETURN MAX_ITERATIONS  # or ESCALATED
```

## Usage Example

```python
from cohezion.eval.pipeline import EvalPipeline, RalphLoop
from cohezion.rl.task_generator import TaskGenerator
from cohezion.sandbox.isolation import get_isolation_manager

# Generate task specs
generator = TaskGenerator(seed=42)
task_specs = generator.generate_all()

# Setup pipeline
manager = get_isolation_manager()
pipeline = EvalPipeline(
    isolation_manager=manager,
    progress_path=Path("data/eval/EVAL_PROGRESS.md"),
    git_auto_commit=True,
)

# Run evaluation
for task_spec in task_specs:
    results = pipeline.run(
        task_spec=task_spec,
        n_episodes=5,
        use_swarm_advisor=False,
    )
    
    for result in results:
        print(f"{result.episode_id}: {result.status.value}")
```

## Git Integration

EvalPipeline auto-commits after every 10 successful episodes:

```bash
git add data/eval/EVAL_PROGRESS.md
git commit -m "eval: record progress - 42 successful episodes"
```

This creates a historical record of evaluation progress linked to code state.

## Isolation Integration

Episodes run in sandboxed isolation via `IsolationManager`:

```python
context = isolation_manager.setup_filesystem(
    base_path="/tmp/eval",
    snapshot_backend="overlay",
)

# Run episode in isolated environment
result = pipeline.run(task_spec, n_episodes=1)

# Cleanup
isolation_manager.cleanup(context)
```

## Files

- `src/cohezion/eval/pipeline.py` - EvalPipeline and RalphLoop implementation
- `tests/eval/test_pipeline.py` - Unit tests
- `docs/phases/PHASE_6_PIPELINE.md` - This documentation
