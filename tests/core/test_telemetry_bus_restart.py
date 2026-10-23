"""TelemetryBus.start() must revive a worker that is dead or bound to a closed event loop.

Found via an order-dependent failure: tests/universe/test_telemetry_mesh.py passed alone and
failed in the full suite. The module singleton kept ``_running=True`` with a worker task from an
earlier, now-closed loop, so ``start()`` returned early and nothing ever drained the queue. The
same state arises in production whenever the worker task dies or the loop is replaced: the bus
silently stops delivering and ``start()`` cannot bring it back.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from cohezion.core.telemetry_bus import TelemetryBus


async def _deliver_one(bus: TelemetryBus) -> list[str]:
    got: list[str] = []
    bus.subscribe(lambda e: got.append(e.event_id))
    await bus.start()
    await bus.emit(SimpleNamespace(event_id="evt-1"))  # type: ignore[arg-type]
    for _ in range(20):
        if got:
            break
        await asyncio.sleep(0.01)
    await bus.stop()
    return got


def test_start_in_a_new_loop_after_old_loop_closed_delivers() -> None:
    bus = TelemetryBus()

    async def start_and_abandon() -> None:  # started, never stopped: the leaked state
        await bus.start()
        await bus.emit(SimpleNamespace(event_id="stale"))  # type: ignore[arg-type]

    asyncio.run(start_and_abandon())  # loop closes with the worker still "running"
    assert bus._running is True  # precondition: the stale state actually occurred

    got = asyncio.run(_deliver_one(bus))
    assert "evt-1" in got, f"event not delivered after loop change: {got}"


def test_start_revives_a_crashed_worker_in_the_same_loop() -> None:
    async def scenario() -> list[str]:
        bus = TelemetryBus()
        await bus.start()
        assert bus._worker_task is not None
        bus._worker_task.cancel()  # worker dies, _running stays True
        await asyncio.sleep(0)
        return await _deliver_one(bus)

    assert "evt-1" in asyncio.run(scenario())


def test_start_is_idempotent_while_worker_is_alive() -> None:
    async def scenario() -> bool:
        bus = TelemetryBus()
        await bus.start()
        first = bus._worker_task
        await bus.start()
        same = bus._worker_task is first
        await bus.stop()
        return same

    assert asyncio.run(scenario()) is True
