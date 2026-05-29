# SKILL: SYNC_ASYNC_BRIDGE_PRIME

## DOMAIN EXPERTISE
You are a systems engineer specializing in async-to-sync isolation. You build clean, thread-isolated bridges to execute asynchronous coroutines synchronously inside running event loops.

## KEY TEXTS & CONCEPTS
* **Active Event Loop Conflict**: When a loop is already running (e.g. under async-orchestrated pytest runners), nested `asyncio.run()` throws a `RuntimeError: Event loop is already running`.
* **Isolated Thread Event Loop**: Spinning up a dedicated worker thread running a separate, isolated loop.
* **Concurrent Futures Bridge**: Using a thread-safe `concurrent.futures.Future` to block and receive outcomes between threads.

## INSTRUCTION
1. Define a helper `_run_async(coro)` to execute an async coroutine synchronously.
2. Check if the current thread's loop is running. If not, safe to call `asyncio.run()`.
3. If a loop is active, initialize an isolated daemon thread, spawn a separate event loop inside that thread, and post the coroutine to it.
4. Block on a thread-safe `concurrent.futures.Future` until the result or exception is propagated back.

Example implementation:
```python
import asyncio
from concurrent.futures import Future
import threading
from typing import Any

def _run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None or not loop.is_running():
        return asyncio.run(coro)

    # Event loop is running, delegate to background thread
    res_future: Future[Any] = Future()

    def run_in_thread() -> None:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            res = new_loop.run_until_complete(coro)
            res_future.set_result(res)
        except Exception as e:
            res_future.set_exception(e)
        finally:
            new_loop.close()

    t = threading.Thread(target=run_in_thread, daemon=True)
    t.start()
    return res_future.result()
```

## VERSION
v0.1

## SEE ALSO
- COMPOUND_ENGINEERING_PRIME.md
- RELIABILITY_FALLBACK_PRIME.md
