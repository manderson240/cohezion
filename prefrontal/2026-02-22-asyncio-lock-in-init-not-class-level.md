---
title: 'Move asyncio.Lock from Class-Level to __init__'
date: 2026-02-22
status: accepted
tags: [decision, asyncio, python, testing, singleton]
aspect: thinker
neural:
  activation: 0.74
  stage: growing
  synapse_in: 3
  synapse_out: 8
---
# Decision: Move asyncio.Lock from Class-Level to __init__

**Date**: 2026-02-22
**Project**: [[cohezion]]
**Status**: Implemented
**Session**: 70

## Context

`ResourceMonitor` had `_lock: asyncio.Lock = asyncio.Lock()` as a class-level attribute. This lock is created at import time, bound to the initial event loop. When pytest creates fresh async event loops per test, 12+ tests became ERRORs. Tests passed individually but failed in the full suite — the classic isolation failure signature.

The root cause is that `asyncio.Lock()` captures a reference to the running event loop at construction time. When declared at class level (outside `__init__`), the lock binds to whatever loop exists when the module is first imported. Pytest's `asyncio_mode=strict` creates a new event loop per test or test group, so the class-level lock is forever bound to a stale (closed) loop. Any `await self._lock.acquire()` then raises `RuntimeError: Task got Future attached to a different loop`.

This is a specific instance of a broader pattern: **asyncio primitives must never be class-level attributes in singleton classes**. The same issue applies to `asyncio.Semaphore`, `asyncio.Event`, `asyncio.Condition`, and `asyncio.Queue`.

## Decision

Remove `_lock` from class attributes. Add `self._lock: asyncio.Lock = asyncio.Lock()` inside `__init__`, alongside `self.semaphore = asyncio.Semaphore()`. All asyncio synchronization primitives are created per-instance, not per-class.

## Rationale

asyncio.Lock objects are bound to the event loop that creates them. Class-level creation at import time binds the lock to whatever event loop existed at module import. Pytest creates new event loops per async test group, causing stale lock errors. Instance-level creation in `__init__` guarantees freshness, and the singleton reset fixture (`ResourceMonitor._instance = None`) forces `__init__` to re-run per test.

## Consequences

**Positive:**
- All 12 previously failing tests pass in the full suite
- Tests are properly isolated — each test group gets a fresh lock bound to its own event loop
- The singleton reset fixture (`_instance = None`) naturally triggers `__init__`, creating fresh primitives
- Pattern is generalizable to all asyncio primitives in singleton classes

**Negative:**
- Slightly more code in `__init__` (minor)
- Developers must remember to never add asyncio primitives at class level — requires discipline or a linting rule

## Alternatives Considered

**Lazy initialization (`@property` with None check):** Would work but adds complexity. `__init__` is simpler and already runs at the right time via singleton reset. Rejected for unnecessary indirection.

**`asyncio.Lock()` at class level with loop re-binding:** Not supported by the asyncio API — locks cannot be rebound to a new event loop after creation. Rejected as infeasible.

**Disable `asyncio_mode=strict` in pytest:** Would mask the problem by allowing tests to share an event loop. Rejected because shared event loops cause test pollution — the strict mode is correct.

## Related

- [[async-singleton-lock-isolation]] — the pattern that generalizes this fix to all async singleton classes
- [[2026-02-22-pytestmark-asyncio-module-level]] — sibling decision from the same session about async test configuration
- [[2026-02-23-always-set-pytest-timeouts-for-async-tests]] — async test hygiene: timeouts catch the hangs that stale locks cause
- [[service-class-singleton-pattern]] — the singleton pattern that this decision refines for async contexts
- [[2026-02-17-singleton-consolidation-mandatory-during-file-splits]] — related decision about singleton correctness during refactoring
- [[async-mock-subprocess-in-tests]] — another async testing pattern from the same session
- [[2026-02-22-session-70-heal-and-test-fix]]
- KEY_LEARNINGS.md L130
