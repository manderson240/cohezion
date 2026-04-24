"""PrecipitationBus — async fan-out for PrecipitationEvent.

Minimal in-process bus. Producers call `emit(event)` (sync) or `aemit(event)` (async).
Subscribers register a callback keyed by PrecipitationKind (or None for all kinds).

Design constraints:
  - Sync callers (ExoticVacuumObject, Cosmogony) must not block on I/O.
    `emit()` enqueues; a background drainer dispatches to subscribers asynchronously.
  - Sinks (vault/surreal/git) are subscribers; sink failure logs but does not raise.
  - Single process only — no external broker. Cross-process coordination goes
    through the SurrealSink, which is the durable store.

This is not a general-purpose event bus. It is specifically the spine for Cosmogony
Step 10 precipitation. Keep it lean.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable

from .events import PrecipitationEvent, PrecipitationKind


logger = logging.getLogger(__name__)

SubscriberFn = Callable[[PrecipitationEvent], None | Awaitable[None]]

# Default queue capacity. ~10k events ≈ a few MB; much more suggests the drainer
# is wedged and we should log loudly rather than grow unbounded.
_DEFAULT_CAPACITY = 10_000


class PrecipitationBus:
    """In-process fan-out for PrecipitationEvents.

    Subscribers may be sync or async callables. The drainer awaits coroutines
    and catches exceptions so that one bad sink cannot wedge the stream.
    """

    def __init__(self, capacity: int = _DEFAULT_CAPACITY) -> None:
        self._capacity = capacity
        self._queue: asyncio.Queue[PrecipitationEvent] | None = None
        self._queue_loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[PrecipitationKind | None, list[SubscriberFn]] = {}
        self._drainer_task: asyncio.Task[None] | None = None
        self._drainer_lock = threading.Lock()
        self._stopped = False
        self._emitted_count = 0
        self._delivered_count = 0
        self._failure_count = 0

    def subscribe(
        self,
        callback: SubscriberFn,
        kind: PrecipitationKind | None = None,
    ) -> None:
        """Register a callback. kind=None receives every kind."""
        self._subscribers.setdefault(kind, []).append(callback)

    def unsubscribe(self, callback: SubscriberFn) -> None:
        """Remove a callback from all kinds. No-op if not found."""
        for subs in self._subscribers.values():
            while callback in subs:
                subs.remove(callback)

    def emit(self, event: PrecipitationEvent) -> None:
        """Non-blocking enqueue. Safe to call from synchronous code.

        If no event loop is running in this thread, the event is dispatched
        synchronously to sync subscribers and async ones are skipped with a
        warning — a precipitation should never be lost just because no loop
        exists. (Tests frequently call sync code directly.)

        If the running loop differs from the one the queue was bound to (e.g.
        a stale singleton left over from a previous pytest-asyncio test), we
        also fall back to sync dispatch so we don't touch a queue tied to a
        closed loop.
        """
        self._emitted_count += 1
        loop = self._get_loop_if_any()
        if loop is None or self._queue is None:
            self._dispatch_sync_best_effort(event)
            return
        if self._queue_loop is not None and self._queue_loop is not loop:
            # Cross-loop emission — never try to share asyncio.Queue across loops.
            self._dispatch_sync_best_effort(event)
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                "PrecipitationBus full (capacity=%d); dropping oldest to admit event_id=%s",
                self._capacity,
                event.event_id,
            )
            try:
                _ = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(event)

    async def aemit(self, event: PrecipitationEvent) -> None:
        """Await-friendly emit. Enqueues and returns immediately; dispatch is async."""
        self._emitted_count += 1
        loop = asyncio.get_running_loop()
        if self._queue is None or self._queue_loop is not loop:
            self._queue = asyncio.Queue(maxsize=self._capacity)
            self._queue_loop = loop
        await self._queue.put(event)

    async def start(self) -> None:
        """Launch the background drainer. Idempotent.

        If called under a different event loop than the previous start (e.g. a
        reused bus singleton across tests), we re-create the queue on the
        current loop so `put_nowait` doesn't silently target a dead loop.
        """
        with self._drainer_lock:
            loop = asyncio.get_running_loop()
            if self._drainer_task is not None and not self._drainer_task.done():
                return
            if self._queue is None or self._queue_loop is not loop:
                self._queue = asyncio.Queue(maxsize=self._capacity)
                self._queue_loop = loop
            self._stopped = False
            self._drainer_task = asyncio.create_task(self._drain())

    async def stop(self, *, drain: bool = True) -> None:
        """Stop the drainer. If drain=True, waits for queue to empty first."""
        self._stopped = True
        if self._drainer_task is None:
            return
        if drain and self._queue is not None:
            await self._queue.join()
        self._drainer_task.cancel()
        try:
            await self._drainer_task
        except asyncio.CancelledError:
            pass
        self._drainer_task = None

    async def flush(self) -> None:
        """Block until the queue is empty. Useful in tests."""
        if self._queue is not None:
            await self._queue.join()

    @property
    def stats(self) -> dict[str, int]:
        return {
            "emitted": self._emitted_count,
            "delivered": self._delivered_count,
            "failures": self._failure_count,
            "queue_size": self._queue.qsize() if self._queue else 0,
        }

    # --- internals ---

    async def _drain(self) -> None:
        assert self._queue is not None
        while not self._stopped:
            try:
                event = await self._queue.get()
            except asyncio.CancelledError:
                break
            try:
                await self._dispatch(event)
            finally:
                self._queue.task_done()

    async def _dispatch(self, event: PrecipitationEvent) -> None:
        callbacks = list(self._subscribers.get(event.kind, []))
        callbacks.extend(self._subscribers.get(None, []))
        for cb in callbacks:
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    await result
                self._delivered_count += 1
            except Exception:
                self._failure_count += 1
                logger.exception(
                    "Precipitation sink failed for event_id=%s kind=%s",
                    event.event_id,
                    event.kind.value,
                )

    def _dispatch_sync_best_effort(self, event: PrecipitationEvent) -> None:
        """Called when no event loop is running. Only sync subscribers fire."""
        callbacks = list(self._subscribers.get(event.kind, []))
        callbacks.extend(self._subscribers.get(None, []))
        for cb in callbacks:
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    logger.debug(
                        "Skipping async subscriber %s in sync context; start the bus",
                        getattr(cb, "__qualname__", repr(cb)),
                    )
                    result.close()
                    continue
                self._delivered_count += 1
            except Exception:
                self._failure_count += 1
                logger.exception(
                    "Sync precipitation sink failed for event_id=%s",
                    event.event_id,
                )

    @staticmethod
    def _get_loop_if_any() -> asyncio.AbstractEventLoop | None:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None


_GLOBAL_BUS: PrecipitationBus | None = None
_GLOBAL_BUS_LOCK = threading.Lock()


def get_bus() -> PrecipitationBus:
    """Module-level singleton accessor.

    Matches the pattern used by `cohezion.reliability.get_circuit()` and related
    helpers. Tests can inject a fresh bus via `set_bus()` for isolation.
    """
    global _GLOBAL_BUS
    with _GLOBAL_BUS_LOCK:
        if _GLOBAL_BUS is None:
            _GLOBAL_BUS = PrecipitationBus()
        return _GLOBAL_BUS


def set_bus(bus: PrecipitationBus | None) -> None:
    """Replace the global bus (for tests). None resets to a fresh bus on next get_bus()."""
    global _GLOBAL_BUS
    with _GLOBAL_BUS_LOCK:
        _GLOBAL_BUS = bus


def emit(event: PrecipitationEvent) -> None:
    """Convenience module-level emitter using the singleton bus."""
    get_bus().emit(event)


async def aemit(event: PrecipitationEvent) -> None:
    """Convenience async emitter using the singleton bus."""
    await get_bus().aemit(event)


__all__ = [
    "PrecipitationBus",
    "SubscriberFn",
    "aemit",
    "emit",
    "get_bus",
    "set_bus",
]
