---
title: 'Use pytestmark = pytest.mark.asyncio at Module Level'
date: 2026-02-22
status: accepted
tags: [decision, testing, asyncio, python, pytest]
aspect: thinker
neural:
  activation: 0.472
  stage: growing
  cluster: decisions
---
# Decision: Use pytestmark = pytest.mark.asyncio at Module Level

**Date**: 2026-02-22
**Project**: [[cohezion]]
**Status**: Implemented
**Session**: 70

## Context

`test_specifications.py` had 56 `async def test_*` functions with no `@pytest.mark.asyncio`. With `asyncio_mode=strict` in `pytest.ini`, all async tests must be explicitly marked. All 56 failed with "async def functions are not natively supported".

The project uses `asyncio_mode=strict` (set in `pytest.ini`) to enforce explicit async test marking. This is the correct setting because `auto` mode can silently run async tests in unintended event loops. However, strict mode means every `async def test_*` function must be decorated with `@pytest.mark.asyncio`, and forgetting even one decorator causes a confusing failure that looks like a test infrastructure problem rather than a missing decorator.

With 56 async tests in a single file, managing individual decorators is error-prone and adds visual noise that obscures the actual test logic.

## Decision

Add `pytestmark = pytest.mark.asyncio` at module level (after imports). This applies the mark to all tests in the module automatically. For files that mix sync and async tests, the warning on the sync test is acceptable.

```python
import pytest

pytestmark = pytest.mark.asyncio

# All async def test_* in this file are now marked automatically
async def test_something():
    result = await my_async_function()
    assert result == expected
```

## Rationale

Module-level `pytestmark` eliminates 56 individual decorators, ensures no async test is ever missed, and is easy to audit. This is the standard pytest approach for async-heavy test files.

## Consequences

**Positive:**
- All 56 tests pass without individual decorators
- New async tests added to the file are automatically marked — impossible to forget
- Cleaner test files — less decorator noise, easier to read
- Easy to audit: one line per file instead of checking every function

**Negative:**
- Sync tests in the same module get a harmless warning (pytest ignores the asyncio mark on sync functions)
- Developers unfamiliar with `pytestmark` may not understand where the mark comes from
- Files that are 50/50 sync/async may look misleading — but the project convention handles this

## Enforcement

New rule: files with >50% async tests should use module-level `pytestmark` not per-function decorators.

## Alternatives Considered

**Per-function `@pytest.mark.asyncio`:** Works but requires 56 decorators in this file alone. Missing one causes a confusing failure. Rejected for maintenance burden.

**`asyncio_mode=auto` in pytest.ini:** Would remove the need for any marking, but silently changes event loop behavior in ways that can cause subtle test pollution. Rejected because strict mode is the safer default for [[async-singleton-lock-isolation]].

**pytest plugin for auto-detection:** Third-party plugins exist but add an unnecessary dependency when `pytestmark` is a built-in mechanism. Rejected for simplicity.

## Related

- [[2026-02-22-asyncio-lock-in-init-not-class-level]] — sibling decision from the same session about async lock placement
- [[async-mock-subprocess-in-tests]] — async testing pattern that benefits from module-level pytestmark
- [[async-singleton-lock-isolation]] — asyncio_mode=strict combined with module-level pytestmark prevents missing async marks
- [[2026-02-23-always-set-pytest-timeouts-for-async-tests]] — async test configuration sibling: module-level marks + global timeouts form complete async test hygiene
- [[concept-testing]] — pytestmark is a testing infrastructure pattern for ensuring concept tests with async behavior are correctly configured
- KEY_LEARNINGS.md L132
