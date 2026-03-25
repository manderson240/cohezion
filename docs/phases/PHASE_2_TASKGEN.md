# Phase 2: TaskGenerator + TRIUNE Task Specs

## Status: COMPLETE

**Date**: March 25, 2026  
**Deliverables**: All 21 tests passing, lint clean

## What Was Built

### `TaskSpec` (`src/cohezion/rl/task_generator.py`)

RL task specification dataclass with TRIUNE dominance weights and test oracle.

**Key Fields**:
- `archetype` — One of 5 archetypes
- `horizon` — Max steps per episode
- `interruption_points` — Steps where env pauses
- `noise_level` — Action noise multiplier
- `doer_dominance`, `thinker_dominance`, `knower_dominance` — TRIUNE reward weights
- `exotic_charge_amplitude` — Target exotic charge density
- `kordylewski_gravity` — Swarm gravity strength
- `kordylewski_cloud_id` — Target cloud (L4 or L5)
- `stability_well` — Target StabilityWell name

**Test Oracle**: `validate(evo)` returns `(bool, float)` — validates EVO against archetype-specific success criteria.

### `TaskGenerator` (`src/cohezion/rl/task_generator.py`)

Generates TaskSpecs from archetype + difficulty.

**5 Archetypes**:
1. `hiho_basin` — Navigate to HIHO_Origin stability well
2. `triune_balance` — Maintain Doer/Thinker/Knower equilibrium
3. `interruption_recovery` — Recover SPIN coherence after pause
4. `exotic_charge_tolerance` — Navigate with sustained high exotic charge
5. `kordylewski_orbit` — Maintain orbit around L4/L5 memory cloud

**4 Difficulty Levels** per archetype = **20 TaskSpecs total**

Difficulty scaling:
- Level 1: base_horizon x 1.0, noise x 1.0, charge x 0.5
- Level 2: base_horizon x 1.5, noise x 1.5, charge x 1.0
- Level 3: base_horizon x 2.0, noise x 2.0, charge x 1.5
- Level 4: base_horizon x 3.0, noise x 3.0, charge x 2.0

### Test Coverage (21 tests)

| Test Class | Tests | Status |
|---|---|---|
| `TestTaskSpec` | 5 | ALL PASS |
| `TestTaskGenerator` | 11 | ALL PASS |
| `TestTaskArchetypes` | 5 | ALL PASS |

### Files Created

```
src/cohezion/rl/task_generator.py  # TaskSpec + TaskGenerator (~360 lines)
tests/rl/test_task_generator.py   # 21 tests, all passing
```

## Integration Points

- `FlumeNavEnv` — TaskSpec configures env at reset (horizon, interruption_points, noise)
- `EVOTracker` — TaskSpec validates EVO via `spec.validate(evo)`
- `PPOTrainer` — TRIUNE weights shape the reward function
- `EvalPipeline` — TaskGenerator produces tasks for benchmark runs

## Design Decisions

1. **Difficulty scales horizon + noise + charge simultaneously** — harder tasks are longer, noisier, and more exotic
2. **TRIUNE weights are renormalized to sum to 1.0** — ensures reward is well-defined
3. **Kordylewski cloud assigned randomly (50/50 L4/L5)** — could be made strategic in future
4. **Oracle validation is simple** — coherence-based thresholds; more nuanced validation can be added per archetype

## What's Missing / Future Work

1. **Strategic Kordylewski assignment** — assign cloud based on task archetype, not randomly
2. **Nuanced validation oracles** — current oracles are coherence-thresholds; could add TRIUNE balance scoring, orbit stability scoring
3. **Context injection spec** — `context_injection` flag is set but not yet wired into FlumeNavEnv
4. **Per-archetype reward shaping** — different archetypes may need custom reward functions beyond TRIUNE weights

## Reference

- `docs/FLUME_BENCHMARK_PLATFORM.md` — Overall project plan
- Phase 1 doc: `docs/phases/PHASE_1_EVO.md`
