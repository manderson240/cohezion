# Phase 1: EVO (Etheric Variant Oscillator) Model

## Status: COMPLETE

**Date**: March 25, 2026  
**Deliverables**: All 24 tests passing, lint clean

## What Was Built

### Core Classes

#### `EthericVariantOscillator` (`src/cohezion/rl/evo.py`)

The fundamental data structure representing an agentic journey as an exotic vacuum object.

**TRIUNE SELF States**:
- `doer_state` (12D) — Physical action in axiomatic space
- `thinker_state` (512D) — Reasoning and trajectory planning
- `knower_state` (2048D) — Semantic intent

**Physics Properties**:
- `coherence_amplitude` — Peak HIHO stability reached
- `phase` — Position in HIHO oscillation cycle
- `angular_momentum` — 3D SPIN coherence vector
- `charge` — Rotation x Precession alignment

**Exotic Vacuum Properties**:
- `exotic_charge_density` — Deviation from HIHO vacuum baseline
- `kordylewski_cloud_id` — L4/L5 memory cloud assignment
- `stability_well` — Basin of attraction classification

**Key Methods**:
- `record_step(step_data)` — Append to trajectory
- `update_physics(coherence, step, doer_state)` — Update physics state
- `compute_spin_coherence()` — SPIN alignment metric
- `to_exotic_vacuum_biography()` — Export as JSON-serializable dict
- `get_trajectory_length()` — Including spilled-to-disk data

#### `EVOTracker` (`src/cohezion/rl/evo.py`)

Lifecycle manager for active EVOs.

**Key Methods**:
- `create_evo()` — Create new EVO with unique ID
- `register(evo)` — Track active EVO, evict oldest if at capacity
- `unregister(journey_id)` — Remove from active tracking
- `save_evo(evo)` — Save trajectory to disk as `.npy`, clear RAM
- `classify_stability_well(evo)` — HIHO_Origin / Pure_Awareness / unknown

**Memory Management**:
- Max 20 active EVOs in RAM
- Trajectories saved to `data/evo_trajectories/*.npy`
- 80GB RAM ceiling enforced via `.npy` spillover

### Test Coverage (24 tests)

| Test Class | Tests | Status |
|---|---|---|
| `TestEthericVariantOscillator` | 10 | ALL PASS |
| `TestEVOTracker` | 7 | ALL PASS |
| `TestMemoryManagement` | 2 | ALL PASS |
| `TestTRIUNESelfStates` | 5 | ALL PASS |

### Design Decisions

1. **Memory spillover via `.npy` not `memmap`**: `np.load()` works directly on `.npy` files; memmap requires special handling. Simpler is better here.

2. **Auto-spill not yet implemented**: The 80GB ceiling is enforced manually via `save_evo()`. Auto-spill when `len(trajectory) > 500` is documented as expected behavior in tests.

3. **Kordylewski cloud assignment at creation**: Each EVO is assigned L4 or L5 randomly at creation time. This could be made strategic (based on task archetype) in future.

4. **Stability well classification is simple**: Current implementation only checks HIHO_Origin and Pure_Awareness. More wells can be added.

## Files Created

```
src/cohezion/rl/
├── __init__.py          # Module init
├── evo.py               # EVO + EVOTracker (400+ lines)

tests/rl/
├── __init__.py
└── test_evo.py          # 24 tests, all passing
```

## Integration Points

- `ExperienceCollector` — Can emit EVOs instead of raw journey dicts
- `FlumeNavEnv` — Will emit EVOs per episode (Phase 3)
- `TaskGenerator` — Produces `TaskSpec` that initializes EVO TRIUNE states (Phase 2)
- `PPOTrainer` — Uses EVO physics properties in reward shaping (Phase 4)

## What's Missing / Future Work

1. **Auto-spill**: `len(trajectory) > 500` should auto-save to disk, not just on `save_evo()` call
2. **Kordylewski swarm gravity integration**: The `kordylewski_cloud_id` is assigned but not yet used in physics
3. **Multiple stability wells**: Only HIHO_Origin and Pure_Awareness are classified
4. **TRIUNE state persistence**: Only `doer_state` is saved to disk; `thinker_state` and `knower_state` are in RAM

## Reference

- `docs/architecture/EVO_MODEL.md` — Formal EVO physics specification
- `docs/FLUME_BENCHMARK_PLATFORM.md` — Overall project plan
