---
title: Singleton Executor for Sessions: One Executor Instance Per Session Prevents Resource Leaks
date: 2026-02-23
severity: HIGH
category: architecture
tags: [executor, singleton, sessions, resource-management, python]
status: validated
aspect: knower
neural:
  activation: 0.72
  stage: growing
  synapse_in: 14
  synapse_out: 8
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
- [[scaling-agent-systems]] — the singleton executor reduces the "coordination overhead" the paper identifies as the primary multi-agent tax: per-operation executors (independent resource allocation) compound to hundreds of idle threads; one executor per session (centralized resource pool) is the implementation of centralized resource management that the paper shows outperforms independent agent configurations
- [[async-singleton-lock-isolation]] — complementary singleton disciplines: this lesson scopes ThreadPoolExecutors per session lifecycle; async-singleton-lock-isolation scopes asyncio primitives per event loop. Both prevent cross-context resource leakage through proper singleton lifecycle management. Together they cover the two main async resource categories: thread pools and coroutine synchronization primitives.
- [[lesson-15-system-lockup-2026-01-27]] - System lockup from unbounded agent loops is the catastrophic version of the per-operation executor leak; both require explicit resource lifecycle management
- [[agent-architecture]] - singleton executor is a core architectural pattern for session-scoped agent systems
- [[multi-agent-systems]] - prevents resource exhaustion when multiple agent sessions run concurrently
- [[agentic-ai]] - session-scoped singletons are a production requirement for agentic systems at scale
- [[ai-agents]] - one executor per session lifecycle prevents thread leaks across concurrent agent deployments

## Validation

**Discovered**: Feb 2026 in Cohezion session management design
**Status**: Validated -- thread leaks eliminated after singleton pattern adoption
