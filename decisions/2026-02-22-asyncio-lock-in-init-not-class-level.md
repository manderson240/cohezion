---
title: 'Move asyncio.Lock from Class-Level to __init__'
date: 2026-02-22
status: accepted
tags: [decision]
---
# Decision: Move asyncio.Lock from Class-Level to __init__

**Date**: 2026-02-22
**Project**: [[cohezion]]
**Status**: Implemented
**Session**: 70

## Context

`ResourceMonitor` had `_lock: asyncio.Lock = asyncio.Lock()` as a class-level attribute. This lock is created at import time, bound to the initial event loop. When pytest creates fresh async event loops per test, 12+ tests became ERRORs. Tests passed individually but failed in the full suite — the classic isolation failure signature.

## Decision

Remove `_lock` from class attributes. Add `self._lock: asyncio.Lock = asyncio.Lock()` inside `__init__`, alongside `self.semaphore = asyncio.Semaphore()`.

## Rationale

asyncio.Lock objects are bound to the event loop that creates them. Class-level creation at import time binds the lock to whatever event loop existed at module import. Pytest creates new event loops per async test group, causing stale lock errors. Instance-level creation in `__init__` guarantees freshness, and the singleton reset fixture (`ResourceMonitor._instance = None`) forces `__init__` to re-run per test.

## Related

- [[patterns/async-singleton-lock-isolation]]
- [[experiments/2026-02-22-session-70-heal-and-test-fix]]
- KEY_LEARNINGS.md L130
