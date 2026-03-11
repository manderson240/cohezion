# Unified Mass Sim Pipeline Implementation Plan

Created: 2026-03-07
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Iterations:** Tracks implement->verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation. `Yes` uses git worktree isolation.

## Summary

**Goal:** Make the mass simulation pipeline actually work end-to-end: (1) integrate the pure-Python FlumePhysics fallback so simulations run without the Rust extension, (2) fix the HIHO bounds metric so it reflects reality instead of showing 0%, and (3) replace the broken overnight_driver.py with a working CLI entry point.

**Architecture:** The mass_sim module already has a well-designed orchestrator/runner/factory architecture. We integrate the Python fallback into `universe_factory.py`, fix the bounds metric in `flume_physics_py.py`, add the missing CLI driver `mass_sim_driver.py`, and add tests.

**Tech Stack:** Python 3.10+, numpy, asyncio, pytest

## Scope

### In Scope

- Pure-Python `FlumePhysicsPy` class (numpy-based fallback for Rust `cohezion_core_rs`)
- Auto-fallback in `universe_factory.py` (try Rust, fall back to Python)
- CLI driver `mass_sim_driver.py` (entry point for `run_mass_sim.sh`)
- HIHO bounds metric fix: add `pct_elements_within_bounds` (per-element mean), keep old `pct_within_bounds` for backward compat
- Stronger HIHO damping default (`0.01` -> `0.05`) so agents converge within bounds while preserving diversity
- Unit tests for `FlumePhysicsPy` and the bounds metric
- Integration test: demo-scale run produces .npy output

### Out of Scope

- Rust extension compilation (that's a separate build toolchain task)
- overnight_driver.py LLM swarm approach (fundamentally different system, intentionally replaced)
- SurrealDB persistence (already works, no changes needed)
- VAE training pipeline (downstream consumer, not modified)

## Prerequisites

- Access to `/tmp/flume-fix` worktree (contains working prototype code)
- `uv` package manager installed
- Feature branch `feat/flume-vae-clean` accessible via git
- **Pre-implementation check:** Diff the mass_sim module between `/tmp/flume-fix` and the spec worktree to identify ALL files that need copying. The module has 10 .py files (agent_factory, analysis, artifacts, batch_runner, config, exporter, flume_physics_py, __init__, orchestrator, persistence, system_monitor, universe_factory). Files not explicitly modified in the plan should be copied verbatim from `/tmp/flume-fix`.

## Context for Implementer

- **Patterns to follow:** The existing mass_sim module at `src/cohezion/mass_sim/` uses dataclass configs, factory pattern for universe creation, and asyncio orchestration. Follow these patterns.
- **Key files:**
  - `src/cohezion/mass_sim/config.py` — ScaleTier, SimulationConfig (has `delta_scale`, `hiho_damping` params)
  - `src/cohezion/mass_sim/universe_factory.py` — Creates FlumePhysics instances, currently crashes without Rust
  - `src/cohezion/mass_sim/batch_runner.py` — Inner epoch loop, calls `simulate_epochs_batch/navigated`
  - `src/cohezion/mass_sim/orchestrator.py` — Top-level async runner
- **Gotchas:**
  - The `within_bounds` metric requires ALL 256 dims in [0.3, 0.7] per agent. With 256 dims, even 99% per-dim accuracy gives ~7% of agents fully in bounds. The metric needs to be per-dimension-mean, not all-or-nothing.
  - `overnight_driver.py` imports `cohezion.swarm.mass_simulator.MassSimulator` which doesn't exist. This file is dead code.
  - The `run_mass_sim.sh` script already calls `mass_sim_driver.py` correctly — only the Python file was missing.
  - Agent states start as `normal(0.5, 0.25)` — some initial values are already outside [0, 1].

## Feature Inventory

### Files Being Replaced/Modified

| Old File | Functions/Classes | Mapped to Task |
|----------|-------------------|----------------|
| `overnight_driver.py` | Dead code (broken imports) | Intentionally REMOVED — replaced by `mass_sim_driver.py` (Task 3) |
| `universe_factory.py` | `_import_flume_physics()` | Task 1 (fallback logic) |

### New Files

| New File | Purpose | Task |
|----------|---------|------|
| `src/cohezion/mass_sim/flume_physics_py.py` | Pure-Python FlumePhysics | Task 1 |
| `mass_sim_driver.py` | CLI entry point | Task 3 |
| `tests/mass_sim/test_flume_physics_py.py` | Unit tests for physics | Task 4 |
| `tests/mass_sim/test_bounds_metric.py` | Bounds metric tests | Task 5 |
| `tests/mass_sim/test_integration.py` | End-to-end integration | Task 6 |

## Progress Tracking

- [ ] Task 1: Pure-Python FlumePhysics fallback
- [ ] Task 2: HIHO bounds metric fix
- [ ] Task 3: CLI driver (mass_sim_driver.py)
- [ ] Task 4: Unit tests for FlumePhysicsPy
- [ ] Task 5: Bounds metric tests
- [ ] Task 6: Integration test (demo-scale run)

**Total Tasks:** 6 | **Completed:** 0 | **Remaining:** 6

## Implementation Tasks

### Task 1: Pure-Python FlumePhysics Fallback

**Objective:** Create `FlumePhysicsPy` class that implements the same interface as the Rust `FlumePhysics` extension using numpy, and wire up auto-fallback in `universe_factory.py`.

**Dependencies:** None

**Files:**

- Create: `src/cohezion/mass_sim/flume_physics_py.py`
- Modify: `src/cohezion/mass_sim/universe_factory.py`

**Key Decisions / Notes:**

- Reference implementation exists at `/tmp/flume-fix/src/cohezion/mass_sim/flume_physics_py.py`
- Architecture: 2-layer MLP (z_dim -> hidden_dim -> z_dim) with LayerNorm, ReLU, HIHO damping
- `_import_flume_physics()` in universe_factory.py must try Rust first, fall back to Python
- Remove the `RuntimeError("Rust FlumePhysics extension not compiled")` line
- Methods required: `__init__`, `simulate_epochs_batch`, `simulate_epochs_navigated`, `compute_batch_stats`
- `simulate_epochs_navigated` uses global `np.random.randn()` — intentionally non-deterministic. Tests should only verify output differs from batch mode, not check specific values.

**Definition of Done:**

- [ ] `FlumePhysicsPy` class exists with all 3 public methods
- [ ] `universe_factory.py` auto-falls back to Python when Rust unavailable
- [ ] `from cohezion.mass_sim.universe_factory import UniverseFactory` succeeds without Rust

**Verify:**

- `cd /path/to/worktree && uv run python -c "from cohezion.mass_sim.universe_factory import UniverseFactory; print('OK')"`

### Task 2: HIHO Bounds Metric Fix

**Objective:** Add a new `pct_elements_within_bounds` metric (per-element mean) alongside the existing `pct_within_bounds` (kept for backward compat), and increase default `hiho_damping` from 0.01 to 0.05 to balance convergence with diversity.

**Dependencies:** Task 1

**Files:**

- Modify: `src/cohezion/mass_sim/flume_physics_py.py` (bounds calculation in `compute_batch_stats`, default `hiho_damping` param)
- Modify: `src/cohezion/mass_sim/config.py` (default `hiho_damping`)
- Modify: `src/cohezion/mass_sim/universe_factory.py` (default `hiho_damping` param in `create()`)

**Key Decisions / Notes:**

- Keep existing `pct_within_bounds` (all-dims-per-agent) for backward compat — downstream consumers like `analysis.py` use this key with threshold semantics.
- Add NEW `pct_elements_within_bounds`: `np.mean((agents >= 0.3) & (agents <= 0.7))` — fraction of all (agent, dim) pairs in bounds. This is the meaningful measure for monitoring.
- Also add `pct_agents_majority_in_bounds`: fraction of agents where >80% of dims are in bounds.
- Increase `hiho_damping` default from `0.01` to `0.05` in ALL three locations: `SimulationConfig` (config.py), `UniverseFactory.create()` (universe_factory.py), and `FlumePhysicsPy.__init__()` (flume_physics_py.py). The damping formula is `z_new = z_new + damping * (0.5 - z_new)`, so 0.05 means 5% pull per step — enough to keep agents centered while preserving diversity (dim_stds > 0.01).
- **Why 0.05 not 0.1:** At damping=0.1, agents collapse to z=0.5 after ~100 epochs, destroying diversity. At 0.05, convergence is slower but steady-state dim_stds remain meaningful (~0.02-0.05).
- Replace the misleading config.py comment `# 0.01 is the empirically optimal value: coherence ~0.51, 96% within [0.3, 0.7]` with: `# 0.05 provides 5% pull toward 0.5 per step — balances convergence within HIHO bounds with diversity preservation`.

**Definition of Done:**

- [ ] `compute_batch_stats` returns `pct_elements_within_bounds` (per-element) AND keeps `pct_within_bounds` (all-or-nothing, backward compat)
- [ ] `compute_batch_stats` also returns `pct_agents_majority_in_bounds`
- [ ] `SimulationConfig.hiho_damping` default is `0.05`
- [ ] Default `hiho_damping` param is `0.05` in all 3 files (config, factory, physics)
- [ ] Config comment updated to explain the value
- [ ] After 100 epochs with damping=0.05, `dim_stds` mean > 0.01 (diversity preserved)

**Verify:**

- `cd /path/to/worktree && uv run python -c "
from cohezion.mass_sim.flume_physics_py import FlumePhysicsPy
import numpy as np
rng = np.random.default_rng(42)
fp = FlumePhysicsPy(rng.normal(0,0.05,(512,256)).astype(np.float32), np.zeros(512,dtype=np.float32), rng.normal(0,0.05,(256,512)).astype(np.float32), np.full(256,0.02,dtype=np.float32), np.ones(512,dtype=np.float32), np.full(512,0.5,dtype=np.float32), hiho_damping=0.05)
agents = rng.normal(0.5, 0.25, (100, 256)).astype(np.float32)
evolved = fp.simulate_epochs_batch(agents, 100)
stats = fp.compute_batch_stats(evolved)
print(f'pct_elements_within_bounds={stats[\"pct_elements_within_bounds\"]:.2%}')
print(f'pct_agents_majority={stats[\"pct_agents_majority_in_bounds\"]:.2%}')
import statistics; dim_std_mean = statistics.mean(stats['dim_stds'])
print(f'dim_stds_mean={dim_std_mean:.4f}')
assert stats['pct_elements_within_bounds'] > 0.5, 'Bounds metric should be >50%'
assert dim_std_mean > 0.01, 'Diversity should be preserved (dim_stds > 0.01)'
"`

### Task 3: CLI Driver (mass_sim_driver.py)

**Objective:** Create the missing CLI entry point that `scripts/overnight/run_mass_sim.sh` calls.

**Dependencies:** Task 1, Task 2

**Files:**

- Create: `mass_sim_driver.py` (project root)

**Key Decisions / Notes:**

- Reference implementation exists at `/tmp/flume-fix/mass_sim_driver.py`
- Args: `--scale` (demo/medium/overnight/aspirational), `--max-mem`, `--output-dir`, `--agents/--epochs/--universes` overrides, `--no-db`, `--no-export`
- Uses `MassSimOrchestrator` from the mass_sim module
- The `run_mass_sim.sh` script already calls `uv run python mass_sim_driver.py --scale ${SCALE} --max-mem 100 --output-dir data/mass_sim/artifacts`
- Log format matches existing mass_sim logging style
- When using Python fallback (no Rust) AND `--scale overnight`, log a WARNING: "Python fallback active. Overnight scale estimated at ~700+ hours. Consider --scale medium (~1.5h) instead."
- Add `--hiho-damping` and `--delta-scale` CLI args so users can experiment without editing source
- Fix the double-construction of SimulationConfig from the prototype (lines 89-104 create it twice when --output-dir is set)

**Definition of Done:**

- [ ] `mass_sim_driver.py` exists at project root
- [ ] `uv run python mass_sim_driver.py --help` shows usage
- [ ] `uv run python mass_sim_driver.py --scale demo --no-db` completes without error

**Verify:**

- `cd /path/to/worktree && uv run python mass_sim_driver.py --help`
- `cd /path/to/worktree && uv run python mass_sim_driver.py --scale demo --no-db --no-export --agents 10 --epochs 100 --universes 2`

### Task 4: Unit Tests for FlumePhysicsPy

**Objective:** Test the pure-Python physics engine: forward pass shape, epoch simulation convergence, and determinism.

**Dependencies:** Task 1

**Files:**

- Create: `tests/mass_sim/__init__.py`
- Create: `tests/mass_sim/test_flume_physics_py.py`

**Key Decisions / Notes:**

- Test cases:
  1. `test_forward_output_shape` — verify `_forward(z)` returns [batch, z_dim]
  2. `test_step_applies_hiho_damping` — verify states move toward 0.5
  3. `test_simulate_epochs_batch_deterministic` — same input/weights = same output
  4. `test_simulate_epochs_navigated_has_noise` — output differs from batch (stochastic)
  5. `test_compute_batch_stats_keys` — verify all expected keys present
- Use small z_dim (8) and hidden_dim (16) for fast tests
- Seed everything for determinism

**Definition of Done:**

- [ ] All 5 test cases pass
- [ ] Tests run in <2 seconds total
- [ ] No external dependencies (pure numpy)

**Verify:**

- `cd /path/to/worktree && uv run pytest tests/mass_sim/test_flume_physics_py.py -v`

### Task 5: Bounds Metric Tests

**Objective:** Test that the fixed `pct_within_bounds` metric behaves correctly for known distributions.

**Dependencies:** Task 2

**Files:**

- Create: `tests/mass_sim/test_bounds_metric.py`

**Key Decisions / Notes:**

- Test cases:
  1. `test_all_in_bounds_returns_100_pct` — agents all at 0.5 should give 100%
  2. `test_all_out_of_bounds_returns_0_pct` — agents all at 0.0 should give ~0%
  3. `test_mixed_bounds_gives_expected_fraction` — half in, half out = ~50%
  4. `test_majority_metric_counts_agents` — agents with >80% dims in bounds

**Definition of Done:**

- [ ] All 4 test cases pass
- [ ] Tests verify per-element metric, not all-or-nothing

**Verify:**

- `cd /path/to/worktree && uv run pytest tests/mass_sim/test_bounds_metric.py -v`

### Task 6: Integration Test (Demo-Scale Run)

**Objective:** Verify the full pipeline works end-to-end: orchestrator -> physics -> export -> .npy files.

**Dependencies:** Task 1, Task 2

**Files:**

- Create: `tests/mass_sim/test_integration.py`

**Key Decisions / Notes:**

- Run a tiny scale: 10 agents, 50 epochs, 2 universes
- This test uses `MassSimOrchestrator` directly, NOT the CLI driver (Task 3 is independent)
- Verify:
  - Orchestrator completes without error
  - Report has correct structure (universes, agent-epochs, artifacts)
  - .npy files created with correct shape [n_agents, z_dim]
  - `pct_within_bounds` > 0 in final stats
- Use `--no-db` to skip SurrealDB dependency
- Use tmp directory for artifacts
- Mark with `@pytest.mark.asyncio` and set timeout

**Definition of Done:**

- [ ] Integration test passes
- [ ] Produces .npy files with correct shape
- [ ] `pct_within_bounds` > 0 in report
- [ ] Test runs in <30 seconds

**Verify:**

- `cd /path/to/worktree && uv run pytest tests/mass_sim/test_integration.py -v --timeout=60`

## Testing Strategy

- **Unit tests:** FlumePhysicsPy forward pass, step behavior, stats computation (Task 4)
- **Metric tests:** Bounds metric correctness with known distributions (Task 5)
- **Integration test:** Full pipeline demo run producing .npy output (Task 6)
- **Manual verification:** `uv run python mass_sim_driver.py --scale demo --no-db` (Task 3 verify step)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Python fallback too slow for overnight scale | High | High | Overnight scale (10K agents x 100K epochs x 1K universes) is infeasible with Python — estimated ~700+ hours (weeks, not hours). CLI driver must log a warning when `--scale overnight` is used without Rust and suggest `--scale medium` instead. Medium scale (~1.5h) is the realistic Python ceiling. |
| HIHO damping=0.05 overcorrects (agents lose diversity) | Low | Medium | Verify step checks `dim_stds` mean > 0.01 after 100 epochs. If diversity is too low, damping can be reduced to 0.03. |
| Missing `uv` or wrong Python version in worktree | Low | Low | Verify `uv run python --version` in Task 3 verify step. |

## Open Questions

- None — all three deliverables are well-defined with working prototype code in `/tmp/flume-fix`.

### Deferred Ideas

- Compile Rust extension for 10x speedup (separate build toolchain task)
- Add progress bar with `tqdm` for interactive runs
- Stream results to SurrealDB during simulation (currently batch at end)
- Parallelize universe execution with `asyncio.gather` + semaphore for N-way concurrency (would cut medium-scale wall time significantly on the 32-core Ryzen)
- Accept optional `np.random.Generator` in `FlumePhysicsPy` for reproducible navigated simulation
- Add matplotlib to optional deps and make artifact generation gracefully optional
