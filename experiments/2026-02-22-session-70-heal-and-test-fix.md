---
title: 'Session 70 — Heal + Test Fix Cycle (83 → 0 failures)'
date: 2026-02-22
status: complete
tags: [experiment]
---
# Experiment: Session 70 — Heal + Test Fix Cycle (83 → 0 failures)

**Date**: 2026-02-22
**Project**: [[cohezion]]
**Session**: 70

## Hypothesis

Running /heal (lint + format + package integrity) followed by systematic test failure root cause categorization would reduce 83 FAILED + 15 ERROR to zero in a single session.

## Method

**Phase 1: /heal**
- `ruff check --fix`: 1,799 errors found → 913 auto-fixed
- `ruff format`: 222 files reformatted
- 17 missing `__init__.py` created (real_envs/, research/, swarm/agents/specialized/, eval/, cosmic/, etc.)
- Remaining lint: 823 errors (non-auto-fixable)

**Phase 2: Root Cause Categorization**
Ran each failing file individually — all passed! Confirmed isolation pattern.
Six root causes identified:
1. `_holographic_project` typo at `journey_tracker.py:408` (method renamed L→public but internal call not updated)
2. `critical_pressure: float = 0.0` type mismatch (Session 68 changed bool→float, test still checks `is False`)
3. `asyncio.Lock` at class level — stale across event loops (12 ERRORs in full suite)
4. `curl` subprocess calls with no timeout → hang when Ollama unavailable
5. `asyncio.Future as side_effect` on MagicMock → await hangs forever (never resolved)
6. 56 async tests in `test_specifications.py` missing `@pytest.mark.asyncio`

**Phase 3: Fixes Applied**
All 6 causes fixed, verified individually then full suite.

## Result

| Metric | Before | After |
|--------|--------|-------|
| Passing | 3,177 | 3,318 |
| Failed | 83 | 0 |
| Errors | 15 | 0 |
| Lint errors | 1,724 | 837 |

## Key Learnings

1. **Categorize before fixing** — 83 failures were only 6 root causes
2. **Run individually first** — all-pass individually = isolation bug, not logic bug
3. **/heal before test investigation** — format changes affect test collection
4. **Private→Public rename drift** — always grep src/ AND tests/ when renaming
5. **asyncio primitives at class level = event loop trap**

## Bidirectional Links

- [[decisions/2026-02-22-post-crash-venv-recovery-pytest-missing-despite-pyprojecttoml|Post-Crash Venv Recovery Decision]] — the companion decision from the same session documenting venv corruption and `uv add --dev` recovery
- [[decisions/2026-02-22-cz-spec-workflow-retrospective|cz spec workflow retrospective]] — same date; the TDD and test suite patterns from this session informed those workflow improvements
- [[2026-02-22-asyncio-lock-in-init-not-class-level]]
- [[2026-02-22-pytestmark-asyncio-module-level]]
- [[async-singleton-lock-isolation]]
- [[async-mock-subprocess-in-tests]]
- [[private-to-public-rename-drift]]
- [[sessions/session-69-retrospective]]
