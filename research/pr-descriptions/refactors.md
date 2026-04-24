---
branch: polish/refactors
base: polish/code-quality
commits: 5 (incremental) / 59 (vs main)
files_changed: 27 (incremental)
loc_delta: +3916 / -3342 (incremental, mostly module relocations)
campaign: synthetic-sniffing-panda (2026-04-23)
campaign_plan: ~/.claude/plans/synthetic-sniffing-panda.md
campaign_retrospective: ~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md
---

# polish/refactors — Three God-File Splits (api, cohezion_mcp, executor)

## Summary
This PR breaks up the three largest "god files" in the codebase. `src/cohezion/api/__init__.py` (~2,000 lines) is split into 13 router modules under `api/routes/`. `src/cohezion/skills/cohezion_mcp.py` (~1,500 lines) is split into 6 focused tool modules. `src/cohezion/compound/executor.py` has three of its largest helpers (vault integration, template matcher, async guardrail runner) extracted into `executor_helpers/`. Net behavior preserved — these are pure mechanical splits, not redesigns.

## Scope
**In scope (3 sub-waves):**
- Wave 2B — `refactor(api): extract 13 router modules from api/__init__.py` (1 commit)
- Wave 2C — `refactor(skills): split cohezion_mcp into focused tool modules` (1 commit)
- Wave 2D — `refactor(executor): extract 3 helpers to executor_helpers/` (3 commits, one per helper)

**Out of scope:**
- Adversarial review of the api split → `polish/research-deep-think` (commit fba90dc27, Ω4)
- Edge-case hunt of the executor refactor → `polish/research-deep-think` (commit e1fa0ee42, Ω5)
- Coverage tests for the new modules → `polish/tests`

## Wave breakdown

### Wave 2B — api/__init__.py split (commit 0ac84a8b5)
Extracts 13 logical router groups into `src/cohezion/api/routes/`:
- `a2a.py`, `agentjet.py`, `compound.py`, `flume_inline.py`, `journeys_legacy.py`, `knowledge.py`, `mcp.py`, `metrics.py`, `notebooks.py`, `rl.py`, `skills.py`, `swarm.py`, `templates.py`
- `_helpers.py` for shared route utilities
- `__init__.py` becomes a thin assembler that imports + mounts each router

### Wave 2C — cohezion_mcp.py split (commit 795d2021b)
Extracts focused tool modules from the monolithic MCP server:
- `mcp_inference_tools.py` — inference + routing tools
- `mcp_model_tools.py` — model lifecycle tools
- `mcp_paths.py` — path constants, no logic
- `mcp_reliability_tools.py` — circuit breaker + degradation tools
- `mcp_skill_tools.py` — skill lifecycle tools
- `mcp_tool_definitions.py` — tool schema declarations (largest split, ~541 lines)

### Wave 2D — executor.py extraction (3 commits)
Each extraction is its own commit so reviewers can verify behavior preservation:
1. `5ac8bdc1a` — `get_experience_guidance()` → `executor_helpers/vault_integration.py` (-81 / +112)
2. `835c9aa8d` — `_try_template_match()` → `executor_helpers/template_matcher.py` (-29 / +56)
3. `dc547dcd6` — `_run_async_guardrail()` → `executor_helpers/guardrail_runner.py` (-33 / +42)

`executor_helpers/__init__.py` re-exports each helper for backwards-compat imports.

## Key metrics
- `api/__init__.py`: ~2,000 lines → ~600 lines (assembly only)
- `cohezion_mcp.py`: ~1,500 lines → split into 7 files, largest is `mcp_tool_definitions.py` (541 lines)
- `executor.py`: -143 lines extracted (3 helpers); main file shrinks toward the 300-line target
- LOC delta on this branch is roughly insertion-heavy because relocations count as both delete (from origin) and insert (in new file) when extracted into new files.

## Test impact
- Pre: 968 passed / 86 failed / 51 errors (after polish/code-quality)
- Post: 968 passed / 86 failed / 51 errors (verified — no regression from refactor)
- The refactors are pure relocations + import re-exports. Public API preserved (verified by adversarial review in Ω4).

## Files changed (categorized — incremental vs polish/code-quality)

| Directory | Files | Change |
|---|---|---|
| `src/cohezion/api/` | 15 | NEW: 13 route modules + `_helpers.py` + modified `__init__.py` |
| `src/cohezion/skills/` | 7 | NEW: 6 mcp tool modules + modified `cohezion_mcp.py` |
| `src/cohezion/compound/` | 5 | NEW: 3 executor_helpers + `__init__.py` + modified `executor.py` |

## Reviewer guide

**Read first (the splits, in order):**
1. `0ac84a8b5` — api split. Diff is large; verify:
   - Each router file exports an `APIRouter` instance
   - `api/__init__.py` mounts each router on the same prefix it had before
   - No route handler was renamed or moved across routers (1:1 lift)
2. `795d2021b` — cohezion_mcp split. Verify each tool file imports the same set of dependencies the original file did, no logic changed.
3. `5ac8bdc1a` → `835c9aa8d` → `dc547dcd6` — executor extractions. Each is small (~60 lines net). Verify the helper signatures match the call sites left in `executor.py`.

**Verify backwards compatibility:**
- All previously-importable symbols still resolve from their original module path. (Re-exports in `__init__.py` files preserve the public API.)
- Run `tests/compound/` — same 968/86/51 baseline.

**Adversarial reviews already in the campaign:**
- `research/reviews/2026-04-23-omega4-api-refactor-review.md` — Ω4 review of Wave 2B
- `research/reviews/2026-04-23-omega5-edge-case-hunt.md` — Ω5 review of Waves 2A+2D
- Both ship in `polish/research-deep-think`. Findings logged in `research/remediation/2026-04-23-omega5-omega6-remediation-plan.md` (Ω12).

## Dependencies
- **Builds on `polish/code-quality`** — the bare-except fixes in Wave 2A modified `api/__init__.py`, `executor.py`, and `cohezion_mcp.py` BEFORE these splits were authored. Cherry-picking refactors without prior bare-except fixes causes a content conflict (verified — see MERGE_PLAN.md "Cherry-pick failures" section).
- **`polish/tests` builds on this** — Wave 3A executor coverage tests reference the extracted helpers.

## Verification recipe
```bash
git checkout polish/refactors
uv run pytest tests/compound/ tests/api/ -q --no-cov  # expect 968 pass / 86 fail / 51 err
# Spot-check public API preservation:
uv run python -c "from cohezion.api import app; print(len(app.routes))"  # expect ~92 route handlers
uv run python -c "from cohezion.skills.cohezion_mcp import *"  # original imports still work
uv run python -c "from cohezion.compound.executor import CompoundExecutor; print('ok')"
```

## Risks
- **Hidden import side-effects**: if any external caller imported a private function (e.g. `executor._run_async_guardrail`), they need to update. Re-exports in `__init__.py` cover the documented public API; the private helpers are now in `executor_helpers/`.
- **Route mounting order**: if any router-level middleware was order-sensitive in the original `api/__init__.py`, the new mount order in `__init__.py` must match. Reviewer should confirm by reading the mounting block.
- **Largeness of single 2B commit**: `0ac84a8b5` is +2055 / -1894 in one commit. Diffing this is unwieldy. Consider reviewing each `api/routes/<file>.py` against the corresponding section of the prior `__init__.py` separately.

## Out of scope (deferred)
- Further executor.py shrinkage (more helpers exist; only top 3 extracted)
- ouroboros/monitor.py refactor (29 mypy errors; proposal lives in `research/refactor-proposals/2026-04-23-ouroboros-monitor-refactor.md` from Ω11)
- Test additions for the new modules (in `polish/tests`)
