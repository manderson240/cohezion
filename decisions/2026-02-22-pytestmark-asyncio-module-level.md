---
title: 'Use pytestmark = pytest.mark.asyncio at Module Level'
date: 2026-02-22
status: accepted
tags: [decision]
---
# Decision: Use pytestmark = pytest.mark.asyncio at Module Level

**Date**: 2026-02-22
**Project**: [[cohezion]]
**Status**: Implemented
**Session**: 70

## Context

`test_specifications.py` had 56 `async def test_*` functions with no `@pytest.mark.asyncio`. With `asyncio_mode=strict` in `pytest.ini`, all async tests must be explicitly marked. All 56 failed with "async def functions are not natively supported".

## Decision

Add `pytestmark = pytest.mark.asyncio` at module level (after imports). This applies the mark to all tests in the module automatically. For files that mix sync and async tests, the warning on the sync test is acceptable.

## Rationale

Module-level `pytestmark` eliminates 56 individual decorators, ensures no async test is ever missed, and is easy to audit. This is the standard pytest approach for async-heavy test files.

## Enforcement

New rule: files with >50% async tests should use module-level `pytestmark` not per-function decorators.

## Related

- [[2026-02-22-asyncio-lock-in-init-not-class-level]]
- [[async-mock-subprocess-in-tests]]
- [[async-singleton-lock-isolation]] — asyncio_mode=strict combined with module-level pytestmark prevents missing async marks
- [[2026-02-23-always-set-pytest-timeouts-for-async-tests]] — async test configuration sibling: module-level marks + global timeouts form complete async test hygiene
- KEY_LEARNINGS.md L132
