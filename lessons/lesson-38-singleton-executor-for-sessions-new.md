---
title: Singleton Executor for Sessions: One Executor Instance Per Session Prevents Resource Leaks
date: 2026-02-23
severity: HIGH
category: architecture
tags: [executor, singleton, sessions, resource-management, python]
status: validated
---

# Lesson: Singleton Executor for Sessions: One Executor Instance Per Session Prevents Resource Leaks

## Context

Each agent session was creating its own ThreadPoolExecutor for async task execution. With multiple concurrent sessions, this created hundreds of idle threads and leaked file descriptors.

## Core Learning

**Use a singleton executor shared across all operations within a session. Scope the singleton to the session lifecycle.**

### Pattern
```python
class SessionExecutor:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def run(self, fn, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, fn, *args)

    def shutdown(self):
        self._executor.shutdown(wait=True)
        SessionExecutor._instance = None

# Session start
executor = SessionExecutor.get()

# Session end (in finally block)
executor.shutdown()
```

## Recommendations

### Do
- Create ONE executor per session at session initialization
- Register executor shutdown in atexit or finally blocks
- Monitor active thread count to detect executor leaks

### Don't
- Create executors inside operation functions (per-operation lifecycle)
- Forget to call shutdown() at session end

## Related Concepts

- [[compound-engineering]] - Resource-efficient execution enables compound session scaling

## Validation

**Discovered**: Feb 2026 in Cohezion session management design
**Status**: Validated -- thread leaks eliminated after singleton pattern adoption
