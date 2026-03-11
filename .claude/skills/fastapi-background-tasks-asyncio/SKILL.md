---
name: fastapi-background-tasks-asyncio
description: |
  Fix for two related FastAPI/Starlette bugs involving BackgroundTasks and asyncio:
  (1) "RuntimeError: no running event loop" when wrapping asyncio.create_task()
  in a lambda passed to background_tasks.add_task(). Solution: pass the async
  function directly, not wrapped in a lambda.
  (2) Starlette TestClient runs BackgroundTasks synchronously — performance tests
  that expect fast response times will fail because background execution is included.
  Use when tests fail with "no running event loop" or performance assertions fail
  on endpoints that use BackgroundTasks.
author: Claude Code
version: 1.0.0
---

# FastAPI BackgroundTasks + asyncio Bugs

## Bug 1: "RuntimeError: no running event loop"

### Problem

Wrapping `asyncio.create_task()` in a lambda passed to `BackgroundTasks.add_task()`
causes a `RuntimeError: no running event loop` at runtime.

### Root Cause

`BackgroundTasks.add_task()` executes the callable in a sync context during ASGI
shutdown. When the lambda runs, there is no event loop active, so
`asyncio.create_task()` fails.

### Fix

Pass the async function **directly** — FastAPI knows how to schedule coroutines:

```python
# WRONG — lambda runs asyncio.create_task() in sync context
background_tasks.add_task(lambda: asyncio.create_task(my_async_fn()))

# CORRECT — pass the coroutine function directly
background_tasks.add_task(my_async_fn)
# Or with args:
background_tasks.add_task(my_async_fn, arg1, arg2)
```

FastAPI's `BackgroundTasks` detects whether the callable is a coroutine function
(`asyncio.iscoroutinefunction()`) and awaits it appropriately.

---

## Bug 2: TestClient Runs BackgroundTasks Synchronously

### Problem

Performance tests that measure response time for endpoints using `BackgroundTasks`
fail because the measured time includes full background task execution.

```python
# This test FAILS — elapsed includes background task runtime
start = time.time()
response = client.post("/api/start", json=config)
elapsed = time.time() - start
assert elapsed < 0.5  # Fails: took 10+ seconds
```

### Root Cause

Starlette's `TestClient` (built on `requests` + ASGI transport) runs background
tasks **synchronously** within the `.post()` / `.get()` call, before returning
the response object. This differs from real production behavior where background
tasks run after the response is sent.

### Fix

Mock out the background task's heavy work when testing response time:

```python
from unittest.mock import patch, AsyncMock

with patch.object(MyService, "heavy_method", new_callable=AsyncMock):
    start = time.time()
    response = client.post("/api/start", json=config)
    elapsed = time.time() - start

assert elapsed < 0.5  # Now passes — background task is mocked
assert response.status_code == 200
```

Or use `httpx.AsyncClient` with `anyio` for true async behavior where background
tasks are not awaited inline.

## Verification

```bash
# Test should pass quickly now
uv run pytest tests/api/test_endpoints.py::test_response_time -v
```
