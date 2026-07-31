"""EventBus.stop() must drain the queue instead of deadlocking on it.

Finding #2 of the DataMesh adversarial stress review (see
tests/data_mesh/test_eventbus_datamesh_stress.py) diagnosed this race in the test
layer and routed AROUND it — `_cancel_bus()` cancels the processor task directly
because `stop()` hangs. The production defect was never closed, so every caller of
the documented shutdown API could hang forever AND silently lose the queued events:

    stop():          self._running = False   -> then await self._queue.join()
    _process_loop(): while self._running:    -> sees False, exits WITHOUT draining
                     ... so task_done() is never called and join() waits forever.

Observed live 2026-07-31 publishing to the datamesh bus: `publish()` returned True,
`stop()` never returned, and the event never reached SurrealDB.

These tests are discriminating — both fail (TimeoutError / lost event) against the
set-flag-before-join ordering.
"""

from __future__ import annotations

import asyncio

import pytest

from cohezion.core.event_bus import Event, EventBus, EventType


def _event(**payload) -> Event:
    return Event(type=EventType.CUSTOM, source="shutdown-test", payload=dict(payload))


@pytest.mark.asyncio
async def test_stop_returns_and_does_not_deadlock_on_a_nonempty_queue():
    bus = EventBus()
    seen: list[str] = []

    async def handler(event: Event) -> None:
        # Guarantees the item is still unprocessed when stop() is entered.
        await asyncio.sleep(0.05)
        seen.append(event.source)

    bus.register_handler(handler, EventType.CUSTOM)
    await bus.start()
    await bus.publish(_event(n=1))

    # Old ordering: _running=False -> loop exits -> task_done() never called -> hangs.
    await asyncio.wait_for(bus.stop(), timeout=5.0)
    assert seen == ["shutdown-test"], "stop() must drain queued events, not drop them"


@pytest.mark.asyncio
async def test_stop_drains_every_queued_event_not_just_the_first():
    bus = EventBus()
    seen: list[int] = []

    async def handler(event: Event) -> None:
        await asyncio.sleep(0.01)
        seen.append(event.payload["n"])

    bus.register_handler(handler, EventType.CUSTOM)
    await bus.start()
    for n in range(10):
        await bus.publish(_event(n=n))

    await asyncio.wait_for(bus.stop(), timeout=10.0)
    assert sorted(seen) == list(range(10)), f"lost events on shutdown: {sorted(seen)}"


@pytest.mark.asyncio
async def test_stop_is_idempotent_and_safe_on_an_empty_queue():
    bus = EventBus()
    await bus.start()
    await asyncio.wait_for(bus.stop(), timeout=5.0)
    # A second stop must not hang or raise (processor already cancelled).
    await asyncio.wait_for(bus.stop(), timeout=5.0)


@pytest.mark.asyncio
async def test_stop_without_start_is_a_noop():
    bus = EventBus()
    await asyncio.wait_for(bus.stop(), timeout=5.0)


@pytest.mark.asyncio
async def test_stop_clears_running_even_without_a_processor_task():
    """`start()` sets `_running = True` BEFORE `create_task()`, so a task-creation failure
    leaves the flag set with no processor to clear it. Clearing `_running` only inside
    `if self._processor_task:` would strand the bus in a permanently-'running' state."""
    bus = EventBus()
    bus._running = True  # simulate start() having set the flag before create_task() failed
    assert bus._processor_task is None
    await asyncio.wait_for(bus.stop(), timeout=5.0)
    assert bus._running is False
