---
title: "Cohezion Orphan Module Audit (Real, Empirical)"
date: 2026-04-24
campaign: synthetic-sniffing-panda Wave Σ5b
methodology: empirical scan of src/cohezion/ + grep-based external-importer count, content inspection, pyproject.toml + CLAUDE.md cross-reference
supersedes: any prior audit claiming 'datamesh', 'elegant_core', or 'infrastructure' as targets — those modules do not exist in this repo
---

# Method

For each top-level module under `src/cohezion/`, counted:
- File count (`*.py` files)
- Total LOC (sum of file lines)
- External importers — any `*.py` file outside the module's own dir that does `from cohezion.<module>` or `import cohezion.<module>` (regex match)
- Test count — files under `tests/` whose path contains the module name
- Last commit date

Then for the bottom of the importer-rank list (`ext_imp <= 2`), additionally checked:
- `__init__.py` content
- File-by-file content (looking for stub code, broken imports, prototypes)
- CLAUDE.md mentions
- `pyproject.toml` references (ruff per-file-ignores, mypy overrides)
- `skill_registry.json` string references
- Filesystem-path mentions (NOT real imports — false positives in raw grep)

# Per-module findings (sorted by external importers, ascending)

| Module | Files | LOC | Ext importers | Tests | Last commit | Recommendation |
|---|---|---|---|---|---|---|
| pipelines | 2 | 51 | 0 | 0 | 2026-03-25 | **DELETE** — broken stub, no users |
| reporting | 2 | 91 | 0 | 0 | 2026-04-24 | **DELETE** — prototype, no users |
| storage | 2 | 54 | 0 | 0 | 2026-03-25 | **DELETE** — old port 8000, replaced by core/persistence |
| cli | 3 | 937 | 0 | 0 | 2026-03-11 | **DEFER** — CLAUDE.md mentions, tied to services |
| real_envs | 3 | 139 | 0 | 0 | 2026-03-21 | **DELETE** — broken stub, imports non-existent evaluator |
| traceability | 3 | 486 | 0 | 0 | 2026-03-30 | **DEFER** — referenced in pyproject.toml, real impl |
| skills | 11 | 1840 | 0 | 1 | 2026-04-24 | **KEEP** — skill registry (.md files), CLAUDE.md anchor |
| benchmarks | 3 | 1468 | 1 | 2 | 2026-03-25 | **KEEP** — has dedicated test file |
| optimization | 2 | 49 | 2 | 3 | 2026-03-25 | **KEEP** — used by swarm/cost_aware_router |
| services | 5 | 1718 | 2 | 7 | 2026-04-01 | **KEEP** — used by cli/main.py |
| ... (62 modules with ext_imp >= 3, all healthy) | ... |

(Full table: see `/tmp/sigma5b_orphan_scan.txt`. 67 total modules scanned; only the bottom 10 candidates investigated for deletion.)

# Recommendations

## Confirmed orphans — will delete in this PR

### `pipelines/` (51 LOC)
- 0 external importers (verified: `grep -rln "from cohezion.pipelines\|import cohezion.pipelines" src tests` returns empty)
- 0 tests
- Not mentioned in `CLAUDE.md`
- Not in `pyproject.toml`
- Contents: `traceability.py` defines `TraceabilityPipeline` and `TraceabilityLink` — a separate prototype from the SurrealDB-backed `traceability/` module
- **Verdict:** Dead prototype. Safe to delete.

### `reporting/` (91 LOC)
- 0 external importers
- 0 tests
- Only string mention is in `docs/archive/SOVEREIGN_CONTEXT.md`
- Contents: `nightly.py` defines `NightlyReporter` for compound engineering reports
- Replaced by the `compound/` module's own metrics/reporting pipeline
- **Verdict:** Dead prototype. Safe to delete.

### `storage/` (54 LOC)
- 0 external importers (only string match was `qdrant_path = "...cohezion/storage/memory/..."` — filesystem path, NOT a Python import)
- 0 tests
- Contents: `surreal_client.py` connects to `ws://localhost:8000` (OLD PORT — current is 8001 via `core/persistence/surreal_client.py`, see CLAUDE.md)
- **Verdict:** Superseded by `core/persistence/`. Safe to delete.

### `real_envs/` (139 LOC)
- 0 external importers
- 0 tests
- Contents: `tasks/scenarios.py` imports `from cohezion.real_envs.evaluator import (...)` — but `evaluator.py` DOES NOT EXIST in the module
- Git log: commit `7c9d4ffc5 fix: create scenarios.py stub to fix test collection error` confirms this was a stub fix
- **Verdict:** Broken stub. Safe to delete.

## Probable orphans — DEFER (insufficient evidence for safe deletion)

### `traceability/` (486 LOC)
- 0 external importers (only self-import: `register_plan.py` -> `plan_graph.py`)
- Referenced in `pyproject.toml` ruff per-file-ignores (lint-only, not runtime)
- Has a SurrealDB schema sibling: `knowledge_graph/plan_traceability_schema.surql`
- Real implementation: `PlanGraph` + `register_plan` over httpx
- **Verdict:** Looks intentionally orphaned (wired-at-creation pending). Defer until owner confirms.

### `cli/` (937 LOC)
- 0 actual `cohezion.cli` importers
- BUT: importable via `python -m cohezion.cli`
- Mentioned in CLAUDE.md (twice)
- Tightly couples to `services/` (which has its own dependents)
- **Verdict:** Defer — entry-point candidate, deletion would silently disable a CLI surface.

## False alarms (low importer count but actively used)

### `skills/` — 0 ext_imp via Python grep
- BUT: 235 skill `.md` files referenced via `skill_registry.json` and runtime skill discovery
- CLAUDE.md anchor: "236 skill definitions (215 PRIME)"
- **Not an orphan** — the importer count was misleading because skills are loaded via filesystem walk, not Python imports.

### `benchmarks/` — 1 ext_imp
- `tests/benchmarks/test_agentic_metrics.py` exercises `cohezion.benchmarks.agentic_metrics.AgenticResults`
- **Not an orphan** — actively tested.

### `optimization/` — 2 ext_imp
- `src/cohezion/swarm/cost_aware_router.py` imports from it
- **Not an orphan**.

### `services/` — 2 ext_imp
- `src/cohezion/cli/main.py` imports `agent_service`, `knowledge_service`, `physics_service`, `swarm_service`
- **Not an orphan** — backbone of the CLI.

## Existing data_mesh integration (verified by Σ5b)

- `src/cohezion/data_mesh/data_product.py` exposes `get_cohezion_data_products()`
- `src/cohezion/compound/capability_matrix.py:517` defines `enrich_from_data_mesh()` which calls `get_cohezion_data_products()` (line 529-531)
- **No additional wiring needed**, contradicting any earlier campaign claim that data_mesh was orphaned.

# Action plan (this PR)

## Will delete (high confidence — 4 modules, 335 LOC reclaimed)
- [ ] `src/cohezion/pipelines/` (51 LOC)
- [ ] `src/cohezion/reporting/` (91 LOC)
- [ ] `src/cohezion/storage/` (54 LOC)
- [ ] `src/cohezion/real_envs/` (139 LOC)

Each deletion: separate commit, post-delete `pytest tests/compound/ -q` floor check (>= 1039 passing). On regression, immediate `git reset --hard HEAD~1` and reclassify.

## Will NOT delete (insufficient evidence)
- `cli/`, `traceability/` — defer to owner

## Will NOT touch (out of scope — healthy modules)
- All 57+ modules with ext_imp >= 3
- `skills/`, `benchmarks/`, `optimization/`, `services/` (false alarms)
- `data_mesh/` (already wired into `compound/capability_matrix.py:517`)

# Notes

The earlier Wave 5B audit prompt referenced three modules that DO NOT EXIST in this repo:
- `cohezion.datamesh` — not present (the real module is `data_mesh` with underscore, and it's already wired)
- `cohezion.elegant_core` — not present
- `cohezion.infrastructure` — not present

Σ5b regenerated the entire orphan list from empirical scan rather than trusting the fabricated list.
