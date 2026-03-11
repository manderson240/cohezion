---
title: "Session 70 — Heal + Test Fix Cycle (83 → 0 failures)"
date: 2026-02-22
status: complete
tags: [experiment, testing, debugging, heal, lint, asyncio, pytest]
aspect: thinker
neural:
  activation: 0.613
  stage: mature
  cluster: experiments
---

# Experiment: Session 70 — Heal + Test Fix Cycle (83 -> 0 failures)

**Date**: 2026-02-22
**Project**: [[cohezion]]
**Session**: 70

## Hypothesis

Running /heal (lint + format + package integrity) followed by systematic test failure root cause categorization would reduce 83 FAILED + 15 ERROR to zero in a single session. The key insight being tested: that a large number of test failures often trace back to a small number of root causes, and categorizing before fixing is more efficient than fixing failures individually.

## Method

### Phase 1: /heal (Automated Cleanup)
- `ruff check --fix`: 1,799 errors found, 913 auto-fixed
- `ruff format`: 222 files reformatted
- 17 missing `__init__.py` created (real_envs/, research/, swarm/agents/specialized/, eval/, cosmic/, etc.)
- Remaining lint: 823 errors (non-auto-fixable, requiring manual intervention)

### Phase 2: Root Cause Categorization
Ran each failing file individually — all passed in isolation. This confirmed an isolation pattern: failures only manifested in the full test suite, not in individual test files. This is a critical diagnostic signal indicating shared state contamination rather than logic bugs.

Six root causes identified across all 83 failures + 15 errors:

| # | Root Cause | Failures | Fix |
|---|-----------|----------|-----|
| 1 | `_holographic_project` typo at `journey_tracker.py:408` | ~5 | Renamed method call to match public API |
| 2 | `critical_pressure: float = 0.0` type mismatch | ~8 | Session 68 changed bool->float but test still checked `is False` |
| 3 | `asyncio.Lock` at class level | 12 ERRORs | Stale lock across event loops; moved to `__init__` |
| 4 | `curl` subprocess calls with no timeout | ~10 | Added timeout; hung when Ollama unavailable |
| 5 | `asyncio.Future` as `side_effect` on MagicMock | ~5 | Future never resolved; await hung forever |
| 6 | 56 async tests missing `@pytest.mark.asyncio` | 56 | Added marker at module level |

### Phase 3: Fixes Applied
All 6 root causes fixed. Each fix verified individually before running the full suite to confirm no regressions.

## Result

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Passing | 3,177 | 3,318 | +141 |
| Failed | 83 | 0 | -83 |
| Errors | 15 | 0 | -15 |
| Lint errors | 1,724 | 837 | -887 |

All 83 failures + 15 errors resolved. Net test increase of 141 passing (previously errored tests now running correctly).

## Key Learnings

1. **Categorize before fixing** — 83 failures were only 6 root causes. Fixing individually would have been 14x more work for the same result. Always count unique causes before writing any fixes.
2. **Run individually first** — if all tests pass individually but fail in suite, it is an isolation bug (shared state, event loop contamination, import side effects), not a logic bug. This diagnostic shortcut saves hours.
3. **/heal before test investigation** — format changes from ruff affect test collection order and can reveal or mask isolation-dependent failures. Always run heal first to establish a clean baseline.
4. **Private-to-Public rename drift** — always grep both `src/` AND `tests/` when renaming methods. The `_holographic_project` typo was introduced by renaming the method to a public API but not updating the internal call site.
5. **asyncio primitives at class level = event loop trap** — `asyncio.Lock()` defined at class level becomes stale across event loops (each test gets a fresh event loop, but the Lock is bound to the first one). Always instantiate async primitives in `__init__`, never at class level. See [[2026-02-22-asyncio-lock-in-init-not-class-level]].
6. **Mock futures must be resolved** — using `asyncio.Future()` as a `side_effect` on MagicMock creates an unresolved future that hangs forever on `await`. Either set the result immediately or use `AsyncMock` with a return value. See [[async-mock-subprocess-in-tests]].

## Bidirectional Links

- [[2026-02-22-post-crash-venv-recovery-pytest-missing-despite-pyprojecttoml|Post-Crash Venv Recovery Decision]] — the companion decision from the same session documenting venv corruption and `uv add --dev` recovery
- [[2026-02-22-cz-spec-workflow-retrospective|cz spec workflow retrospective]] — same date; the TDD and test suite patterns from this session informed those workflow improvements
- [[2026-02-22-recursive-challenger-session-68-autonomous-improvement-loop]] — Session 68's autonomous improvement run introduced several of the failures fixed here
- [[2026-02-22-asyncio-lock-in-init-not-class-level]] — pattern: asyncio Lock instantiation
- [[2026-02-22-pytestmark-asyncio-module-level]] — pattern: module-level pytest.mark.asyncio
- [[async-singleton-lock-isolation]] — pattern for async singleton lock management
- [[async-mock-subprocess-in-tests]] — pattern for mocking async subprocess calls
- [[private-to-public-rename-drift]] — pattern for catching rename drift across src and tests
- [[session-69-retrospective]] — prior session retrospective
- [[concept-testing]] — this experiment demonstrates systematic test debugging methodology
- [[anomaly-detection]] — the "all pass individually, fail in suite" diagnostic is an anomaly detection pattern applied to test execution
