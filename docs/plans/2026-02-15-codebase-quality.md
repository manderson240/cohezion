# Codebase Quality: Highest ROI Sweep

Created: 2026-02-15
Status: VERIFIED
Approved: Yes
Iterations: 1
Worktree: No

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Iterations:** Tracks implement->verify cycles (incremented by verify phase)

## Summary

**Goal:** Eliminate all test failures (14 → 0), fix critical lint bugs, and auto-clean 758 lint warnings — achieving CI-green baseline with maximum token efficiency.

**Architecture:** Three parallel work streams ordered by ROI. Stream 1 is a single command (auto-fix). Stream 2 is the root cause fix for ALL 14 test failures (suite pollution). Stream 3 fixes 3 actual runtime bugs (F821 undefined names).

**Token Budget:** ~1,500 tokens total (vs ~5,000 for naive per-test investigation)

## Key Insight: Single Root Cause

**ALL 14 test failures pass in isolation.** Every failure is suite pollution — tests leaking state into subsequent tests via singleton modules, global caches, or unflushed SurrealDB connections.

| Test File | Failures | Passes Alone? | Root Cause |
|-----------|----------|--------------|------------|
| `test_pre_commit_hooks.py` | 3 | Yes (23/23) | Suite pollution |
| `test_precommit_hooks.py` | 4 | Yes (23/23) | Suite pollution |
| `test_token_client.py` | 2 | Yes (3/3) | Suite pollution |
| `test_hooks.py` | 1 | Yes | Suite pollution |
| `test_experience_pipeline.py` | 1 | Yes | Suite pollution (SurrealDB leak) |
| `test_concurrency.py` | 1 | Yes (1/1) | Suite pollution |
| `test_execution_orchestrator.py` | 1 | Yes (1/1) | Suite pollution |

**Fix one conftest.py, fix all 14 tests.**

## Scope

### In Scope

- Fix test suite pollution (conftest.py session/module fixtures)
- Auto-fix 758 ruff warnings (`ruff check --fix`)
- Fix 3 F821 undefined-name bugs (actual runtime errors)
- Verify 0 test failures, reduced ruff error count

### Out of Scope

- E501 line-too-long (592 occurrences — low ROI per fix, ongoing maintenance)
- S311 suspicious-random (84 — acceptable for AI/ML simulation code)
- S603/S607 subprocess warnings (100 — acceptable for CLI tooling)
- RUF012 mutable-class-default (42 — low risk in this codebase)
- Coverage improvements (currently 11% — separate initiative)

## ROI Analysis

| Stream | Effort | Fixes | ROI Score |
|--------|--------|-------|-----------|
| 1: Auto-fix lint | 1 command | 758 warnings | **100x** (758 fixes / ~10 tokens) |
| 2: conftest.py fix | ~500 tokens | 14 test failures | **28x** (14 failures / ~500 tokens) |
| 3: F821 undefined names | ~200 tokens | 3 runtime bugs | **15x** (3 critical bugs / ~200 tokens) |

**Total: 775 issues resolved in ~1,500 tokens.**

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Auto-fix ruff warnings (652 fixed via safe codes, 198 via formatting = 850 total)
- [x] Task 2: Fix conftest.py suite pollution (14→0 failures, all fixed)
- [x] Task 3: Fix F821 undefined-name bugs (3 runtime errors in tracked files) ✅

**Total Tasks:** 3 | **Completed:** 3 | **Remaining:** 0

**Final Status:**
- **Task 1:** 850 lint warnings auto-fixed (I001, UP045, UP006, W293, UP035, RUF022)
- **Task 2:** All 14 test failures fixed (14→0). Root causes: SurrealDB _SHARED_STORE leak, `%d` log format strings triggering TypeError under pytest LogCaptureHandler
- **Task 3:** All 3 F821 undefined-name bugs in tracked files fixed:
  - `router.py:267` - Added TYPE_CHECKING import for HardwareProfile
  - `democratic_debate.py:198` - Added TYPE_CHECKING import for TokenEfficientClient
  - `model_fallback_strategy.py:451` - Fixed undefined `t` → `ts` in list comprehension
  - Note: 6 additional F821 errors exist in untracked new files (routes_rl.py, mcp_handlers_config.py, mcp_handlers_util.py) — outside this plan's scope

**Verification fixes (applied during spec-verify):**
- Changed `%d`/`%.1f` log format specifiers to `%s` in ollama_gate.py, execution_orchestrator.py, token_client.py (fixed final 4 test failures)
- Replaced hardcoded absolute paths in test_precommit_hooks.py with relative paths (portability fix)
- Extracted `_reset_all_singletons()` helper in conftest.py to eliminate setup/teardown duplication

**Test Results:** 3128 passed, 0 failed, 18 skipped

## Implementation Tasks

### Task 1: Auto-fix ruff warnings (758 auto-fixable)

**Objective:** Run `ruff check src/cohezion/ --fix` to auto-resolve 758 lint warnings (unsorted imports, deprecated annotations, whitespace, etc.)

**Dependencies:** None

**Implementation Steps:**

1. Run `ruff check src/cohezion/ --fix`
2. Run `ruff format src/cohezion/` for consistent formatting
3. Run test suite to verify no regressions: `uv run pytest tests/ -q --tb=short`
4. Report before/after error counts

**Key Decisions / Notes:**

- Auto-fix covers: I001 (268 unsorted imports), UP045 (184 optional annotations), UP006 (106 old-style annotations), W293 (66 whitespace), UP035 (46 deprecated imports), RUF010 (10 f-string conversions), F401/F841/F811 (103 unused imports/variables)
- Safe to run — all fixes are mechanical, type-preserving transformations
- Some F401 (unused imports) may use `--unsafe-fixes` for conditional imports

**Definition of Done:**

- [ ] `ruff check --fix` completed
- [ ] `ruff format` completed
- [ ] Test suite shows no new failures (14 pre-existing failures acceptable)
- [ ] Error count reduced by ~758

**Verify:**

- `ruff check src/cohezion/ --statistics 2>&1 | head -5` — reduced counts
- `uv run pytest tests/ -q --tb=no 2>&1 | tail -1` — no new failures

### Task 2: Fix conftest.py suite pollution (14 test failures → 0)

**Objective:** Identify and fix state leakage between test modules that causes 14 tests to fail when run in suite but pass individually.

**Dependencies:** Task 1 (clean lint baseline first)

**Implementation Steps:**

1. **Identify polluting tests:** Run binary search to find which prior test module poisons each failing module:
   ```bash
   # For each failing test file, find which prior module causes failure
   uv run pytest tests/swarm/test_token_client.py -q  # passes alone
   uv run pytest tests/swarm/ -q  # if fails → pollution is within swarm/
   ```

2. **Audit conftest.py reset fixtures:** Read `tests/conftest.py` and verify all singleton resets cover:
   - FLUME VAE: `cohezion.api._vae_trainer = None`
   - RL Policy: `cohezion.api._rl_policy = None`
   - Logger handlers: `logging.getLogger().handlers.clear()`
   - **Missing resets to investigate:**
     - SurrealDB connections (leaks into experience_pipeline)
     - OllamaGate state (leaks into concurrency tests)
     - Token client singleton state
     - Pre-commit hook module caches

3. **Add missing fixture resets** to `tests/conftest.py`

4. **Verify fix:** `uv run pytest tests/ -q --tb=short` — 0 failures

**Key Decisions / Notes:**

- Known pollution vectors (from CLAUDE.md): FLUME VAE, RL policy, loggers
- New vectors to investigate: SurrealDB `InMemoryStore`, `OllamaGate` semaphore state, token client cache, pre-commit config file caching
- Approach: fix centrally in conftest.py, not per-test — compound defense

**Definition of Done:**

- [ ] Root cause of suite pollution identified for each failure category
- [ ] `tests/conftest.py` updated with missing singleton/state resets
- [ ] `uv run pytest tests/ -q` shows 0 failures
- [ ] Each previously-failing test verified passing both alone and in suite

**Verify:**

- `uv run pytest tests/ -q --tb=no 2>&1 | tail -1` — 0 failures
- `uv run pytest tests/security/ tests/swarm/ tests/flume/ tests/sandbox/ tests/test_concurrency.py tests/test_execution_orchestrator.py -q --tb=short` — 0 failures in cross-module run

### Task 3: Fix F821 undefined-name bugs (3 runtime errors)

**Objective:** Fix 3 `F821 undefined-name` errors — these are actual bugs where code references names that don't exist at runtime.

**Dependencies:** Task 1

**Files:**

- Fix: `src/cohezion/core/routing/router.py:266` — `HardwareProfile` undefined (missing import)
- Fix: `src/cohezion/swarm/democratic_debate.py:197` — `TokenEfficientClient` undefined (missing import)
- Fix: `src/cohezion/swarm/model_fallback_strategy.py:441` — `t` undefined (typo or missing variable)

**Implementation Steps:**

1. Read each file at the error line
2. Add missing import or fix undefined reference
3. Verify: `ruff check src/cohezion/ --select F821` — 0 errors

**Key Decisions / Notes:**

- These are likely missing imports that happen to work because the code paths haven't been hit in tests
- `HardwareProfile` is probably from `cohezion.core.hardware` or similar
- `TokenEfficientClient` is from `cohezion.swarm.token_client`
- `t` in model_fallback_strategy needs investigation — could be `time` or a type variable

**Definition of Done:**

- [ ] `ruff check src/cohezion/ --select F821` returns 0 errors
- [ ] No new test failures introduced
- [ ] Each fix verified by reading the surrounding context

**Verify:**

- `ruff check src/cohezion/ --select F821` — empty output
- `uv run pytest tests/ -q --tb=no 2>&1 | tail -1` — no new failures

## Testing Strategy

- **Primary:** Full suite `uv run pytest tests/ -q` — target 0 failures (currently 14)
- **Smoke test after auto-fix:** Quick module-level runs to catch regressions from import reordering
- **Pollution verification:** Cross-module runs of previously-failing test files together

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auto-fix breaks imports (conditional imports removed) | Low | Medium | Run full test suite after auto-fix; revert individual files if needed |
| conftest.py fix doesn't cover all pollution vectors | Medium | Low | Binary search identifies exact polluting test; targeted fix |
| F821 fixes expose deeper issues | Low | Low | Just add missing imports; underlying code logic unchanged |

## Compound Engineering Notes

**Why this plan is compound-efficient:**

1. **Single root cause (conftest.py)** fixes 14 separate test failures — compound leverage
2. **One command (`ruff --fix`)** resolves 758 warnings — maximum token efficiency
3. **Three F821 fixes** prevent future runtime crashes — preventive compound value
4. **No manual E501 fixes** — 592 low-ROI changes deferred to incremental maintenance
5. **Total effort: ~1,500 tokens for 775 issue resolutions**

**Deferred to future sessions (Low ROI per token):**

| Category | Count | Why Deferred |
|----------|-------|-------------|
| E501 line-too-long | 592 | Manual per-line; better as incremental maintenance |
| S311 suspicious-random | 84 | Acceptable in AI/ML code |
| RUF012 mutable-default | 42 | Low bug risk in this codebase |
| Coverage (11% → 80%) | Many | Separate initiative, different plan |
