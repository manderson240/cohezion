---
title: 'Async Singleton Lock Isolation'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.65
  stage: growing
  synapse_in: 14
  synapse_out: 6
---
# Pattern: Async Singleton Lock Isolation

**Domain**: testing, async, python
**Source**: `src/cohezion/reliability/monitor.py`
**Discovered**: Session 70 — 2026-02-22

## Problem

Singleton classes with `asyncio.Lock` or `asyncio.Semaphore` as class-level attributes fail in pytest suites:
1. Lock created at import time, bound to the initial event loop
2. pytest-asyncio creates fresh event loops per async test group
3. Using stale lock in new event loop → `RuntimeError` or silent ERROR

Tests pass individually, fail in full suite — the classic isolation failure signature.

## Solution

Move all asyncio primitives out of class-level and into `__init__`. Combine with a reset fixture.

```python
# ❌ BAD — lock bound to event loop at import time
class ResourceMonitor:
    _instance: Optional["ResourceMonitor"] = None
    _lock: asyncio.Lock = asyncio.Lock()  # Created once at class definition!

    def __init__(self):
        if self._initialized:
            return
        self.semaphore = asyncio.Semaphore(4)  # Also problematic if class-level

# ✅ GOOD — all asyncio primitives in __init__
class ResourceMonitor:
    _instance: Optional["ResourceMonitor"] = None
    # No asyncio primitives at class level

    def __init__(self, max_concurrency: int = 4):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._lock: asyncio.Lock = asyncio.Lock()          # Fresh per __init__
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)
        self._initialized = True

# Test fixture MUST reset singleton so __init__ re-runs:
@pytest.fixture(autouse=True)
def reset_singleton():
    ResourceMonitor._instance = None
    yield
    ResourceMonitor._instance = None
```

## Detection

Symptom: Tests pass individually but become ERROR in full suite, specifically in async test contexts. Python's RuntimeError often mentions "attached to a different loop".

## Anti-Pattern Table

| Anti-Pattern | Symptom | Fix |
|---|---|---|
| `asyncio.Lock()` at class level | ERRORs only in full suite | Move to `__init__` |
| `asyncio.Semaphore()` at class level | Same | Move to `__init__` |
| Singleton without reset fixture | Pollution between tests | Add `ClassName._instance = None` fixture |

## Related

- [[2026-02-22-asyncio-lock-in-init-not-class-level]]
- [[async-mock-subprocess-in-tests]]
- [[2026-02-23-always-set-pytest-timeouts-for-async-tests]] — timeouts complement lock isolation to prevent zombie test accumulation
- [[2026-02-24-anti-pattern-zombie-test-processes-from-async-event-loop-teardown]] — zombie anti-pattern that proper lock isolation and timeouts together prevent
- KEY_LEARNINGS.md L130

## Decisions That Applied This Pattern

- [[2026-02-09-ollama-context-management]] — the decision to consolidate Ollama model loading into the Model Wrangler; this pattern solves the concurrent request queuing problem identified there

## Scientific Analogues

- [[quantum-entangled-atomic-sensors]] — quantum entanglement achieves precision because each atom maintains an isolated quantum state correlated with, but not bound to, its partner's measurement context. The class-level `asyncio.Lock()` failure documented here is the engineering parallel: the lock is bound at class-definition time to one event loop (one "measurement context"), and using it from a fresh pytest event loop causes runtime collapse — exactly like forcing two entangled atoms into the same measurement basis prematurely. The fix (move lock to `__init__`) creates fresh primitives per instantiation context, maintaining isolation until coordination is explicitly needed.
