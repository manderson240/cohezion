# Concept: Thread-Safe Sync-to-Async Bridge

## Abstract
A concurrency pattern designed to bridge synchronous execution contexts (such as sync test suites or legacy sync systems) with asynchronous coroutines when a parent event loop is already running.

## Context & Motivation
Under async-orchestrated testing environments (e.g., pytest running with async plugins), calling `asyncio.run(coro)` from synchronous methods causes a `RuntimeError: Event loop is already running`.

To bypass this without corrupting or blocking the parent loop:
1. Spin up a separate, isolated background thread as a daemon.
2. Initialize and run a new independent event loop in that thread.
3. Use a thread-safe `concurrent.futures.Future` to communicate results and exceptions across the thread boundary.
4. Block on the future in the sync context.

## Implementation Pattern
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

## Related
* [[LLM-Wiki]]
* [[AutoHarness]]
