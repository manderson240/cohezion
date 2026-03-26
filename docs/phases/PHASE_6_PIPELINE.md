# PHASE 6: Evaluation Pipeline

## Overview

Phase 6 implements the **RalphLoop** — an autonomous FOR-DONE-ESCALATE iteration pattern for FLUME benchmark evaluation — and **EvalPipeline** — a full multi-episode evaluation orchestration layer.

## RalphLoop: FOR-DONE-ESCALATE Pattern

Named after the archetypal autonomous agent, Ralph. The pattern cycles through:
1. **FOR**: Execute episodes iteratively
2. **DONE**: Check convergence criteria at multiple levels
3. **ESCALATE**: Apply strategy mutations when patience is exhausted

### DONE Incantation (4 Convergence Levels)

| Level | Trigger | Description |
|-------|---------|-------------|
| 0 | — | No convergence |
| 1 | mean_coh > 0.8 AND std_coh < 0.05 | Coherence stability |
| 2 | Level 1 + success_rate > 0.9 | Coherence + success |
| 3 | Level 2 + longitudinal significance (p < 0.05) | All metrics + improvement trend |

### Escalation Protocol (4 Levels)

| Level | Action | Rationale |
|-------|--------|-----------|
| 0 | No change | Baseline exploration |
| 1 | Perturb learning rate × 2.0 | Search breadth |
| 2 | Perturb learning rate × 0.5 | Search depth |
| 3 | Reset optimizer state | Full restart |

### Patience Counter

After `patience` consecutive episodes without progress to the next convergence level, escalation level increments. Default: patience=20, min_episodes=10.

## EvalPipeline

Full multi-episode evaluation orchestration:

```
EvalPipeline.run()
    ├── RalphLoop.run(episode_fn)
    │       ├── episode_fn(episode, escalation_level)
    │       │       ├── FlumeNavEnv.reset(task_spec)
    │       │       ├── EthericVariantOscillator.init()
    │       │       └── FOR steps until done/max_steps
    │       │               ├── policy.get_action(state)
    │       │               ├── env.step(action)
    │       │               └── evo.update_physics()
    │       └── PipelineProgress yielded per episode
    │
    ├── All biographies collected
    │
    └── CapabilityScorecard.record_run()
            ├── EVOPhysicsMetrics.compute_all() per biography
            └── Radar chart + longitudinal tracking
```

## Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `RalphLoop` | pipeline.py | FOR-DONE-ESCALATE iteration |
| `RalphLoopConfig` | pipeline.py | Configuration dataclass |
| `EvalPipeline` | pipeline.py | Multi-episode orchestrator |
| `EpisodeStatus` | pipeline.py | Per-episode status enum |
| `PipelineProgress` | pipeline.py | Immutable progress snapshot |

## EpisodeStatus Enum

```
PENDING    — Not yet started
RUNNING    — Currently executing
SUCCESS    — Task succeeded
FAILURE    — Task failed
CONVERGED  — DONE criterion met, loop terminates
DIVERGED   — Stability lost, loop terminates
INTERRUPTED — External interruption
```

## RalphLoop.run() Generator

```python
loop = RalphLoop(config)
for progress in loop.run(episode_fn):
    print(f"[{progress.episode}] coh={progress.mean_coherence:.4f} "
          f"succ={progress.success_rate:.2f} esc={progress.escalation_level}")
    if progress.status == EpisodeStatus.CONVERGED:
        break
```

The `episode_fn(episode, escalation_level)` must return a dict with keys:
- `coherence`: Mean episode coherence
- `success`: Boolean task success
- `reward`: Total episode reward
- `biography`: EVO biography list

## Configuration

```python
RalphLoopConfig(
    max_episodes=1000,
    convergence_levels=3,
    patience=20,
    min_episodes=10,
    hiho_target=0.5,
    coherence_threshold=0.8,
    coherence_std_threshold=0.05,
    success_threshold=0.9,
    p_value_threshold=0.05,
)
```

## Longitudinal Significance (Level 3)

Compares last 10 episodes vs previous 10 using Mann-Whitney U:
- H0: Recent performance ≡ Previous performance
- Reject H0 (p < 0.05) → Level 3 convergence

## Tests

- 40 tests in `tests/eval/test_pipeline.py`
- Covers: RalphLoop convergence, escalation, patience, EvalPipeline integration, PipelineProgress

## Integration Points

- **BenchmarkSuite**: Uses RalphLoop internally for adaptive episode counts
- **CapabilityScorecard**: EvalPipeline feeds scorecard with results
- **CompoundSessionManager**: Can wrap RalphLoop for checkpoint persistence
- **SkillRefiner**: Weak-axis scores inform task curriculum oversampling
