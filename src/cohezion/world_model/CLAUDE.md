# world_model — Local Context

This file loads in addition to the root `CLAUDE.md`. Root applies here too.

**Purpose:** World Model layer — JEPA predictor, SurpriseExplorer, SIGReg.

## Entry points (8 modules)

| Module | Key class(es) | LOC |
|---|---|---|
| `jepa_world_model.py` | `ManifoldEncoder`, `ActionEncoder`, `Predictor` | 693 ⚠ |
| `jepa_world_model_persistent.py` | `JEPAWorldModelPersistent` | 229 |
| `observer.py` | `Observer` | 190 |
| `observer_world_model.py` | `ObserverWorldModel` | 114 |
| `sigreg.py` | `SIGReg` | 66 |
| `surprise_action_gate.py` | `GateOutcome`, `SurpriseActionGate` | 159 |
| `surprise_explorer.py` | `SurpriseRegion`, `SurpriseExplorer` | 248 |
| `surprise_router.py` | `ActionMode`, `SurpriseDecision`, `SurpriseRouter` | 191 |

## Over the 500-LOC limit (decompose non-destructively)

- `jepa_world_model.py` — 693 LOC

## Invariants / notes referencing this package (from harness.md / root CLAUDE.md)

- bugs — never wired AND added to the wrong class (`EnvironmentResponsePredictor`, not `SkillRefiner`),
- - When `lookahead_steps > 1`: coherence = `min(mean(clip(s,0,1)) for s in world_model.simulate_trajectory(state, [zero_action]*k)[1:])` — the trajectory MINIMUM
- - `src/cohezion/compound/lemonade_world_model.py`: `LemonadeWorldModel` implements the gate's world-model interface (`predict_next_state`/`simulate_trajectory`)
- - **Verification**: `uv run pytest tests/compound/test_lemonade_world_model.py -q` → 11 passed; LIVE: `build_live_jepa_gate().check(...)` real GAIA k=3 delegati
- ## EnvironmentResponsePredictor Invariants (#117, 2026-06-27)
- ### ERP1: EnvironmentResponsePredictor predict() returns None with no history

_Auto-generated 2026-07-22 (gen_nested_claude.py): facts deterministic (ast/grep), Purpose from __init__/module docstrings. Validated by scripts/ci/doc_code_consistency.py. Hand-enrich as needed._
