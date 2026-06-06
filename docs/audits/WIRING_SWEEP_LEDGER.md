---
title: "Wiring-sweep ledger — file-level reachability remediation"
created: 2026-06-06
owner: "wiring-sweep loop (session cron 9aa80dae, every :19/:49)"
policy: "NON-DESTRUCTIVE — orphans are WIRED, never deleted. Static import edge only."
baseline: "top-level package orphans = 0 (audit, 2026-06-06). Deepening to FILE level."
termination: "two consecutive full-package passes with 0 unwired → notify + stop."
---

# Wiring-sweep ledger

The package-level V-model audit (`scripts/audits/vmodel_module_audit.py`) reports **0
top-level orphans** — every `src/cohezion/<pkg>` is reachable. This loop deepens to
**file-level**: every `.py` reachable by a static intra-repo `import` edge.

## Classification (each candidate must be sorted before wiring)

A file with zero static `import cohezion…<mod>` edges from *production* code is a
**candidate**, not automatically an orphan. Sort it first:

| Class | Meaning | Action |
|---|---|---|
| **A · genuinely orphaned** | no prod importer, no test, no registry/entry-point use | WIRE to natural consumer or guarded sub-bridge + discriminating test |
| **B · tests-only** | imported by `tests/` but no `src/` module | wire a production consumer OR record as test-covered-only (judgment) |
| **C · `__init__` re-export** | reached via `from .<mod> import X` in a package `__init__` | already wired — verify the re-export uses `X as X` (ruff-safe), record |
| **D · registry / entry-point live** | reached by `skill_registry.json`, filesystem path, CLI entry-point, hook | functionally live — record as wired-by-non-import; do NOT force a fake edge |

The crude grep (`grep compound.<mod>`) over-reports B/C/D as orphans. Per-tick the loop
must classify with `findReferences` / import-grep across BOTH `src/` and `tests/`, and check
`skill_registry.json` + entry-points, before wiring.

## Baseline scan — `compound/` (first package, 2026-06-06)

24 file-level candidates surfaced (NOT yet classified — that is the next ticks' work):

```
agi_reasoning, aimo_reasoning, behavioral_eval, chronos, consortium_instigator,
distillation_engine, dual_loop_optimizer, dynamic_compound_system,
dynamic_system_integration, eco_symphony, experiment_correlator, harness,
hiho_lm_gate, journey_to_training, optimized_session_manager, post_execution,
recursive_trace_router, retrospection_validator, self_improvement_orchestrator,
skill_mutation_queue, skill_refinement_validator, tape_logger, test_basic_import,
thermal_autoresearch_executor, workflow_manager
```

### compound/ — CLASSIFIED (2026-06-06)
- **Class A · genuine orphans: 0 remaining — `compound/` file-level sweep COMPLETE.**
  WIRED (9): hiho_lm_gate, journey_to_training, optimized_session_manager,
  thermal_autoresearch_executor, distillation_engine, dynamic_compound_system,
  dynamic_system_integration, consortium_instigator, agi_reasoning, aimo_reasoning.
- **Class B · tests-only (13)**: behavioral_eval, chronos, dual_loop_optimizer, eco_symphony,
  experiment_correlator, post_execution, recursive_trace_router, retrospection_validator,
  self_improvement_orchestrator, skill_mutation_queue, skill_refinement_validator, tape_logger,
  workflow_manager. Test-covered → not dead; production-consumer wiring is OPTIONAL/lower-priority.
  (Note: `chronos` reclassified A→B — my own `tests/compound/test_chronos.py` covers it.)
- **Class D · registry-live (1)**: harness.
- **WIRED this loop**: `hiho_lm_gate` (was Class A) → re-exported through `compound/__init__.py`
  (`check_quality`/`check_sycophancy`/`ppl_score`), guarded. Edge proven by
  `tests/wiring/test_hiho_lm_gate_wired.py` (asserts the names resolve from the package AND are
  the gate's own objects — fails if the edge is removed). Commit: see git.

### swarm/ — CLASSIFIED (2026-06-06), wiring BLOCKED on a circular import
File-level scan found 12 genuine-A candidates (agent_factory, deterministic_discovery_with_skill_fallback,
hf_modelfile_builder, intelligence_pipeline, latent_research_team, lemonade_model_enhancer,
model_capability_registry, model_capability_registry_resource_safe, ollama_context_manager,
parser_v3_validation_oracle, plasma_swarm_router, triune_integration).

**BLOCKED — circular import surfaced (the wiring did its job).** Attempting to wire `agent_factory`
into `swarm/__init__` + adding the required swarm-importing discriminating test changed pytest's
import order to **swarm-first**, which broke 4 already-green compound wiring tests. Root cause
(PRE-EXISTING, verified at baseline): `compound/dynamic_compound_system.py:70` and
`compound/dynamic_system_integration.py` do **module-scope** `from cohezion.swarm import …`. So
`compound/__init__`'s guarded re-exports of those two modules **silently unbind** under swarm-first
import order (the `contextlib.suppress` swallows the partial-import ImportError). Compound-first
import works; swarm-first does not. This is a latent compound↔swarm cycle that wiring exposed.
Reverted the agent_factory edit; swarm/ deferred to the human-decision item below.

## Swept packages
| Package | Swept | Candidates | A wired | A remaining | B/C/D recorded | Needs-human |
|---|---|---|---|---|---|---|
| compound | **DONE** | 24 | 9 (+aimo_reasoning) | 0 | 13 B + 1 D | 3 (below) |
| swarm | classified | 24 | 0 (BLOCKED) | 12 | — | circular import (below) |

## Needs human decision
- **compound↔swarm circular import (blocks swarm/ wiring).** `compound/dynamic_compound_system.py`
  + `compound/dynamic_system_integration.py` import `cohezion.swarm` at MODULE scope, so their
  `compound/__init__` guarded re-exports silently unbind under swarm-first import order. Resolve the
  cycle (lazy-import swarm inside those modules' functions, OR make the re-exports order-robust)
  before file-level-wiring swarm/. NOT fixed by the loop (architectural / behavior-affecting).
- **`model_capability_registry` vs `model_capability_registry_resource_safe`** — surface-name pair
  in swarm/; verify same-concept (consolidate) vs distinct (rename) before wiring. Hazard, not merge.
- **`ReasoningModel` surface-name duplicate** — both `compound/agi_reasoning.py` and
  `compound/aimo_reasoning.py` define a class `ReasoningModel`. Per non-destructive policy rule 3
  (surface-name duplicates are hazards to VERIFY, not merge blind): confirm whether these are the
  same concept (consolidate) or legitimately distinct (rename one). NOT merged by the loop. The
  wiring re-exports agi's `ReasoningModel` + aimo's distinctive `AIMOScaler`/`ProcessRewardModel`.
- `src/cohezion/compound/test_basic_import.py` — a `test_` file living under `src/` not `tests/`.
  Moving or removing it is destructive; surfaced for a human call (the loop will not touch it).
- **hiho_lm_gate deeper integration** — its MODEL-BASED sycophancy/ppl gate overlaps
  `inference/anti_sycophancy.py` (which has its own heuristic `check_sycophancy_risk`) and AUTODQA.
  Wiring the model gate INTO either would CHANGE behavior → human decision, not an auto-wire. The
  re-export above is the non-behavior-changing edge; deeper integration is deferred to a human.

## Next tick
`compound/` DONE; `swarm/` classified but BLOCKED (circular import — human decision). Advance to
the NEXT unblocked package (e.g. `inference/` or `physics/`): classify file-level, wire genuine
Class-A orphans one per tick. Do NOT re-attempt swarm/ until the compound↔swarm cycle is resolved.
