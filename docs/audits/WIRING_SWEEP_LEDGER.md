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

### Known classifications (seeded — saves the loop re-deriving)
- `chronos` → **Class A (genuine, new 2026-06-06).** `get_chronos()` has no consumer yet.
  Wire target: the OOM/Chronos deconfliction subscriber (backlog **item 12**) — subscribe to
  `memory_pressure` and log `resource_advisory()`. Until item 12 lands, wire a re-export so it's
  import-reachable.
- `skill_mutation_queue` → likely **Class B/D**: harness invariant **CB2** + `tests/unit/compound/
  test_skill_mutation_queue.py` exercise `SkillMutationQueue`; confirm prod consumer before acting.
- `tape_logger` → CLAUDE.md lists `TapeLogger` as a Compound-layer component → likely **Class C/D**
  (re-exported or registry-live); verify the `__init__` edge.
- `test_basic_import` → a stray test file under `src/` (not `tests/`) → flag for **human decision**
  (move to `tests/` or delete is a deletion → surface, don't act).

## Swept packages
| Package | Swept | Candidates | A wired | B/C/D recorded | Needs-human |
|---|---|---|---|---|---|
| compound | partial (scan only) | 24 | 0 | 0 | test_basic_import (stray) |

## Needs human decision
- `src/cohezion/compound/test_basic_import.py` — a `test_` file living under `src/` not `tests/`.
  Moving or removing it is destructive; surfaced for a human call (the loop will not touch it).

## Next tick
Classify the `compound/` candidates (A vs B/C/D) using cross-`src`+`tests` references +
`skill_registry.json`, wire the Class-A ones one per tick with a discriminating test, then
advance to the next package.
