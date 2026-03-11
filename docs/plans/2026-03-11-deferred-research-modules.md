# Deferred Research Modules - Validation & Integration Plan

Created: 2026-03-11
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: No

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)

## Summary

**Goal:** Validate, split, and integrate the deferred research files into the compound engineering loop. Delete speculative infrastructure (gateways/), split oversized files to comply with 300-line limit, and ensure tests pass.

**Architecture:** Split orborous.py into two focused modules (consensus + orchestrator). Trim research_squad.py by removing blocking sync forever-loop. Delete gateways/ (unvalidated infrastructure with 11 files / 1,415 lines).

**Tech Stack:** Python 3.13+, pytest, existing compound/research/swarm modules

## Scope

### In Scope

- Split `orborous.py` (415 lines) into `consensus.py` (~200L) + `orborous.py` (~200L)
- Trim `research_squad.py` (408 lines) to <300 lines by removing `auto_optimize` forever-loop and `__main__` block
- Delete `src/cohezion/gateways/` (speculative infrastructure for unvalidated product — 11 files, 1,415 lines)
- Validate and commit `RESEARCH_SQUAD_PRIME.md` skill
- Fix and validate both test files
- Ensure `uv run pytest tests/research/ -q` passes

### Out of Scope

- Wiring to real `GlobalMetricsAggregator` (simulated metrics are fine for now)
- New features or capabilities beyond what exists in the deferred files
- Refactoring other research module files

## Prerequisites

- Branch: `feat/compound-elegant-simplification` (current)
- All ruff auto-fixes already committed
- Security fixes already committed

## Context for Implementer

- **Patterns to follow:** Existing module pattern in `src/cohezion/research/config.py` — dataclasses with `to_dict()`, clean imports, <300 lines
- **Import chain:** `research/__init__.py` already imports `DegradationSignal`, `OptimizationResult`, `ResearchSquad`, `integrate_with_compound_system` from `research_squad.py` (lines 24-29). These are public API.
- **Key dependency:** `research_squad.py` imports from `cohezion.compound.core.executor`, `cohezion.compound.models`, `cohezion.swarm.orchestrator`
- **Orborous imports:** `orborous.py` imports from `cohezion.research` (the package), creating a circular-ish chain. After split, `consensus.py` should have zero research imports (pure voting logic).
- **Gotcha:** `research_squad.py:121` and `research_squad.py:223` use `import random` inside methods — this is fine but the random results make tests non-deterministic. Tests should seed random or mock.
- **Gotcha:** `research_squad.py:345-361` has `auto_optimize()` with blocking `time.sleep(300)` — this is a sync forever-loop in an otherwise async-friendly codebase. Remove it.
- **Gateways module:** Contains 11 files (api_squad.py, cache_squad.py, consensus_vote.py, flume_squad.py, __init__.py, omnibus.py, security_squad.py, skills_squad.py, swarm_squad.py, universe_squad.py, vault_squad.py). None are imported by production code outside the module.

## Progress Tracking

- [x] Task 1: Split orborous.py into consensus.py + orborous.py
- [x] Task 2: Trim research_squad.py to <300 lines
- [x] Task 3: Delete gateways/ module
- [x] Task 4: Validate and fix test files
- [ ] Task 5: Commit all changes

**Total Tasks:** 5 | **Completed:** 4 | **Remaining:** 1

## Implementation Tasks

### Task 1: Split orborous.py into consensus.py + orborous.py

**Objective:** Split the 415-line file into two focused modules, each under 300 lines.

**Dependencies:** None

**Files:**
- Create: `src/cohezion/research/consensus.py` (~200 lines: ConsensusVote, ConsensusResult, PartyModeConsensus)
- Modify: `src/cohezion/research/orborous.py` (~200 lines: Orborous class only, imports from consensus.py)
- Modify: `src/cohezion/research/__init__.py` (add consensus exports if needed)

**Key Decisions / Notes:**
- `PartyModeConsensus` (lines 53-242) is self-contained — no research imports needed, pure voting logic
- `Orborous` (lines 245-416) depends on `PartyModeConsensus` and `ResearchSquad`
- `ConsensusVote` and `ConsensusResult` dataclasses go with `PartyModeConsensus`
- Update `orborous.py` imports: `from cohezion.research.consensus import PartyModeConsensus`
- `gateways/omnibus.py` imports `from cohezion.research.orborous import Orborous, PartyModeConsensus` — this import path changes after split but omnibus.py will be deleted in Task 3

**Definition of Done:**
- [ ] `consensus.py` < 300 lines, contains PartyModeConsensus + dataclasses
- [ ] `orborous.py` < 300 lines, contains only Orborous class
- [ ] `from cohezion.research.consensus import PartyModeConsensus` works
- [ ] `from cohezion.research.orborous import Orborous` works

**Verify:**
- `wc -l src/cohezion/research/consensus.py src/cohezion/research/orborous.py`
- `uv run python -c "from cohezion.research.orborous import Orborous; print('OK')"`

### Task 2: Trim research_squad.py to <300 lines

**Objective:** Remove the blocking `auto_optimize` forever-loop and `__main__` block to bring the file under 300 lines.

**Dependencies:** None

**Files:**
- Modify: `src/cohezion/research/research_squad.py`

**Key Decisions / Notes:**
- Remove `auto_optimize()` method (lines 335-361): It's a synchronous `while True` loop with `time.sleep(300)` — inappropriate for an async codebase. The Orborous class provides the async equivalent.
- Remove `__main__` block (lines 383-408): Example code that belongs in docs/tests, not production
- Keep `integrate_with_compound_system()` factory (lines 365-380): It's only 16 lines and is part of the public API (re-exported from `__init__.py`)
- After removal: ~335 lines. Further trim: remove unused `Callable` import, simplify docstrings
- Target: <300 lines

**Definition of Done:**
- [ ] `research_squad.py` < 300 lines
- [ ] All public API exports still work (`ResearchSquad`, `DegradationSignal`, `OptimizationResult`, `integrate_with_compound_system`)
- [ ] No import errors

**Verify:**
- `wc -l src/cohezion/research/research_squad.py`
- `uv run python -c "from cohezion.research import ResearchSquad, integrate_with_compound_system; print('OK')"`

### Task 3: Delete gateways/ module

**Objective:** Remove the speculative infrastructure that violates CLAUDE.md principle #5 ("Never write infrastructure for products that don't exist").

**Dependencies:** Task 1 (orborous.py must be updated first since omnibus.py imports from it)

**Files:**
- Delete: `src/cohezion/gateways/api_squad.py` (129 lines)
- Delete: `src/cohezion/gateways/cache_squad.py` (162 lines)
- Delete: `src/cohezion/gateways/consensus_vote.py` (84 lines)
- Delete: `src/cohezion/gateways/flume_squad.py` (126 lines)
- Delete: `src/cohezion/gateways/omnibus.py` (272 lines)
- Delete: `src/cohezion/gateways/security_squad.py` (130 lines)
- Delete: `src/cohezion/gateways/skills_squad.py` (125 lines)
- Delete: `src/cohezion/gateways/swarm_squad.py` (126 lines)
- Delete: `src/cohezion/gateways/universe_squad.py` (126 lines)
- Delete: `src/cohezion/gateways/vault_squad.py` (127 lines)
- Delete: `src/cohezion/gateways/__init__.py` (8 lines)
- Delete: `src/cohezion/gateways/` directory

**Key Decisions / Notes:**
- Omnibus (272 lines) spawns Orborous instances per "gateway" with hardcoded simulated metrics
- CacheGatewaySquad (162 lines) simulates cache optimization with no real integration
- Neither is imported by any production code outside the module itself
- If needed in the future, can be rebuilt from Orborous + real metrics integration

**Definition of Done:**
- [ ] `src/cohezion/gateways/` directory does not exist
- [ ] No import errors anywhere in the codebase referencing gateways

**Verify:**
- `test ! -d src/cohezion/gateways/`
- `uv run python -c "import cohezion; print('OK')"`

### Task 4: Validate and fix test files

**Objective:** Ensure both test files pass with the restructured modules.

**Dependencies:** Task 1, Task 2

**Files:**
- Modify: `tests/research/test_research_squad.py` (fix imports if needed, seed random for determinism)
- Modify: `tests/research/test_compound_integration.py` (fix imports if needed)

**Key Decisions / Notes:**
- `test_research_squad.py` imports from `cohezion.research` — should work after Tasks 1-2 complete
- `test_compound_integration.py` imports `CompoundExecutor`, `ResearchAgent`, `ResearchConfig` — should work
- Tests use `random.uniform()` via `research_squad._run_optimization_experiment` — results vary per run. Tests should be tolerant of this (check ranges, not exact values). Current tests already do this.
- `test_research_squad.py:338` imports `from cohezion.swarm.swarm import Swarm` — verify this import path exists
- Check if `test_optimization_result_calculation` (line 114-120) math is correct given random results

**Definition of Done:**
- [ ] `uv run pytest tests/research/test_research_squad.py -q` passes
- [ ] `uv run pytest tests/research/test_compound_integration.py -q` passes
- [ ] No import errors or deprecation warnings

**Verify:**
- `uv run pytest tests/research/test_research_squad.py tests/research/test_compound_integration.py -q --tb=short`

### Task 5: Commit all changes

**Objective:** Stage and commit the validated changes with a clear commit message.

**Dependencies:** Task 4

**Files:**
- Stage: All modified/created/deleted files from Tasks 1-4
- Stage: `src/cohezion/skills/RESEARCH_SQUAD_PRIME.md`

**Key Decisions / Notes:**
- Use conventional commit: `feat: integrate research squad and orborous self-improvement loop`
- Include the PRIME skill file in this commit
- Do NOT stage gateways/ (deleted in Task 3)
- Verify `git status` shows expected changes before committing

**Definition of Done:**
- [ ] All changes committed
- [ ] `git status` clean (except unrelated files)
- [ ] Commit message follows conventional format

**Verify:**
- `git log --oneline -1`
- `git status --short | wc -l` (should show only unrelated files)

## Testing Strategy

- Unit tests: `tests/research/test_research_squad.py` (14 tests covering degradation detection, optimization, cost tracking, integration points)
- Integration tests: `tests/research/test_compound_integration.py` (5 tests covering real CompoundExecutor flows)
- Manual verification: `uv run python -c "from cohezion.research import ResearchSquad; print('OK')"`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports after orborous split | Medium | Medium | consensus.py has zero research imports — pure dataclasses + voting logic. No circular risk. |
| test_research_squad random failures | Medium | Low | Tests check ranges not exact values. Seed random if flaky. |
| Missing Swarm import path | Medium | Medium | `from cohezion.swarm.orchestrator import SwarmConfig` works (verified). `from cohezion.swarm.swarm import Swarm` needs verification in Task 4. |
| Gateways referenced elsewhere | Low | Medium | Grep entire codebase for `from cohezion.gateways` before deleting. |

## Open Questions

- None — scope is well-defined and all exploration complete.

### Deferred Ideas

- Wire Orborous to real `GlobalMetricsAggregator` instead of simulated metrics
- Add async `auto_optimize` method to Orborous (replacing the deleted sync version)
- Re-implement gateways concept once real metrics integration exists
