"""Adversarial stress tests for EventBus DataMesh event extension.

Six stress dimensions:
  D1 – Volume (500 events, none dropped)
  D2 – Priority ordering (HEALTH_DEGRADED precedes UPDATED)
  D3 – Handler isolation (raising handler doesn't block other types)
  D4 – Wildcard + typed coexistence (both fire for one event)
  D5 – Reset safety (clean metrics/handlers after reset)
  D6 – Enum identity discrimination (no value aliasing)

Notes
-----
- asyncio_mode=strict in pytest.ini requires @pytest.mark.asyncio on every async test.
- All tests use the real EventBus — no mocks.
- reset_event_bus() is called in teardown to prevent cross-test pollution.
- bus.stop() is intentionally avoided in teardown: it sets _running=False before
  queue.join(), which can deadlock when the queue is non-empty.  We cancel the
  processor task directly instead.  That race is reported as Finding #2 below.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from cohezion.core.event_bus import (
    Event,
    EventBus,
    EventType,
    get_event_bus,
    reset_event_bus,
)


# ─── helpers ────────────────────────────────────────────────────────────────


def make_event(event_type: EventType, priority: int = 0, **payload) -> Event:
    return Event(type=event_type, source="stress-test", priority=priority, payload=dict(payload))


async def _cancel_bus(bus: EventBus) -> None:
    """Cancel the processor task without relying on bus.stop().

    bus.stop() sets _running=False BEFORE await queue.join(), which deadlocks
    if the queue still has unprocessed items.  Cancelling directly is safe.
    """
    if bus._processor_task and not bus._processor_task.done():
        bus._processor_task.cancel()
        try:
            await bus._processor_task
        except asyncio.CancelledError:
            pass


# ─── fixture ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def bus() -> AsyncIterator[EventBus]:
    b = EventBus()
    await b.start()
    yield b
    await _cancel_bus(b)
    reset_event_bus()


# ─── D1: Volume ─────────────────────────────────────────────────────────────


class TestVolume:
    """D1 — 500+ DATA_PRODUCT_UPDATED events through a single bus, none dropped."""

    @pytest.mark.asyncio
    async def test_500_events_all_processed(self, bus: EventBus) -> None:
        N = 500
        processed: list[Event] = []

        @bus.subscribe(EventType.DATA_PRODUCT_UPDATED)
        async def handler(event: Event) -> None:
            processed.append(event)

        for i in range(N):
            await bus.publish(make_event(EventType.DATA_PRODUCT_UPDATED, seq=i))

        # Deterministic drain: waits until every task_done() has been called.
        await bus._queue.join()

        metrics = bus.get_metrics()
        assert metrics["published"] == N, (
            f"published counter wrong: expected {N}, got {metrics['published']}"
        )
        assert metrics["dropped"] == 0, f"Events were dropped: {metrics['dropped']}"
        assert len(processed) == N, f"Handler received {len(processed)} events, expected {N}"


# ─── D2: Priority ordering ───────────────────────────────────────────────────


class TestPriorityOrdering:
    """D2 — DOMAIN_HEALTH_DEGRADED (priority=10) must ALL arrive before DATA_PRODUCT_UPDATED (priority=0).

    Events are published in alternating (mixed) order to prove the bus
    re-orders them, not just preserves insertion order.
    """

    @pytest.mark.asyncio
    async def test_health_degraded_precedes_updated(self, bus: EventBus) -> None:
        arrivals: list[EventType] = []

        @bus.subscribe()  # wildcard — sees every event
        async def record(event: Event) -> None:
            arrivals.append(event.type)

        # Mixed order: health, updated, health, updated …
        for i in range(10):
            await bus.publish(make_event(EventType.DOMAIN_HEALTH_DEGRADED, priority=10, seq=i))
            await bus.publish(make_event(EventType.DATA_PRODUCT_UPDATED, priority=0, seq=i))

        await bus._queue.join()

        assert len(arrivals) == 20, f"Expected 20 arrivals, got {len(arrivals)}"

        health_idx = [i for i, t in enumerate(arrivals) if t == EventType.DOMAIN_HEALTH_DEGRADED]
        updated_idx = [i for i, t in enumerate(arrivals) if t == EventType.DATA_PRODUCT_UPDATED]

        assert max(health_idx) < min(updated_idx), (
            f"Priority ordering violated.\n"
            f"  DOMAIN_HEALTH_DEGRADED positions : {health_idx}\n"
            f"  DATA_PRODUCT_UPDATED positions   : {updated_idx}\n"
            "All high-priority events must precede all low-priority events."
        )


# ─── D3: Handler isolation ───────────────────────────────────────────────────


class TestHandlerIsolation:
    """D3 — A raising handler for DATA_PRODUCT_CREATED must not block DATA_PRODUCT_UPDATED delivery."""

    @pytest.mark.asyncio
    async def test_raising_handler_does_not_block_other_type(self, bus: EventBus) -> None:
        updated_received: list[Event] = []

        @bus.subscribe(EventType.DATA_PRODUCT_CREATED)
        async def bad_handler(event: Event) -> None:
            raise RuntimeError("Intentional fault — CREATED handler is broken")

        @bus.subscribe(EventType.DATA_PRODUCT_UPDATED)
        async def good_handler(event: Event) -> None:
            updated_received.append(event)

        await bus.publish(make_event(EventType.DATA_PRODUCT_CREATED))
        await bus.publish(make_event(EventType.DATA_PRODUCT_UPDATED))
        await bus._queue.join()

        assert len(updated_received) == 1, (
            "UPDATED handler must receive its event even when the CREATED handler raises. "
            f"Got {len(updated_received)} deliveries instead of 1."
        )
        assert bus.get_metrics()["errors"] >= 1, (
            "The error from the CREATED handler was not counted in bus._metrics['errors']"
        )


# ─── D4: Wildcard + typed coexistence ────────────────────────────────────────


class TestWildcardAndTypedCoexist:
    """D4 — Publishing one QUALITY_ALERT fires both the typed handler AND the wildcard."""

    @pytest.mark.asyncio
    async def test_both_typed_and_wildcard_fire(self, bus: EventBus) -> None:
        typed_calls: list[Event] = []
        wildcard_calls: list[Event] = []

        @bus.subscribe(EventType.DATA_PRODUCT_QUALITY_ALERT)
        async def typed_handler(event: Event) -> None:
            typed_calls.append(event)

        @bus.subscribe()  # wildcard
        async def wildcard_handler(event: Event) -> None:
            wildcard_calls.append(event)

        await bus.publish(make_event(EventType.DATA_PRODUCT_QUALITY_ALERT))
        await bus._queue.join()

        assert len(typed_calls) == 1, (
            f"Typed QUALITY_ALERT handler called {len(typed_calls)} times, expected 1"
        )
        assert len(wildcard_calls) == 1, (
            f"Wildcard handler called {len(wildcard_calls)} times, expected 1"
        )


# ─── D5: Reset safety ────────────────────────────────────────────────────────


class TestResetSafety:
    """D5 — After reset_event_bus(), get_event_bus() returns a pristine bus."""

    @pytest.mark.asyncio
    async def test_reset_yields_clean_bus(self) -> None:
        # Phase 1: dirty the global bus
        old_bus = await get_event_bus()

        @old_bus.subscribe(EventType.LINEAGE_UPDATED)
        async def stale_handler(event: Event) -> None:
            pass  # pragma: no cover

        await old_bus.publish(make_event(EventType.LINEAGE_UPDATED))
        await old_bus._queue.join()
        old_metrics = old_bus.get_metrics()
        assert old_metrics["published"] >= 1, "Sanity: old bus must have published events"

        # Phase 2: tear down old bus, reset
        await _cancel_bus(old_bus)
        reset_event_bus()

        # Phase 3: fresh bus must have zero state
        new_bus = await get_event_bus()
        try:
            m = new_bus.get_metrics()
            assert m["published"] == 0, f"New bus published={m['published']}, expected 0"
            assert m["delivered"] == 0, f"New bus delivered={m['delivered']}, expected 0"
            assert m["errors"] == 0, f"New bus errors={m['errors']}, expected 0"
            assert m["wildcard_handlers"] == 0, (
                f"New bus has {m['wildcard_handlers']} wildcard handler(s) — stale from old session"
            )
            # stale_handler must not be registered on the new bus
            handlers_for_lineage = new_bus._handlers.get(EventType.LINEAGE_UPDATED, [])
            assert handlers_for_lineage == [], (
                f"New bus inherited {len(handlers_for_lineage)} LINEAGE_UPDATED handler(s) "
                "from previous session"
            )
        finally:
            await _cancel_bus(new_bus)
            reset_event_bus()


# ─── D6: Enum identity discrimination ────────────────────────────────────────


class TestEnumIdentityDiscrimination:
    """D6 — QUALITY_ALERT subscriber must NOT fire when UPDATED is published.

    If two EventType members shared an integer value (value aliasing), the wrong
    handler would trigger.  This test catches that regression.
    """

    @pytest.mark.asyncio
    async def test_quality_alert_handler_silent_for_updated_event(self, bus: EventBus) -> None:
        alert_calls: list[Event] = []
        updated_calls: list[Event] = []

        @bus.subscribe(EventType.DATA_PRODUCT_QUALITY_ALERT)
        async def alert_handler(event: Event) -> None:
            alert_calls.append(event)

        @bus.subscribe(EventType.DATA_PRODUCT_UPDATED)
        async def updated_handler(event: Event) -> None:
            updated_calls.append(event)

        # Publish ONLY DATA_PRODUCT_UPDATED
        await bus.publish(make_event(EventType.DATA_PRODUCT_UPDATED))
        await bus._queue.join()

        assert len(updated_calls) == 1, "UPDATED handler must fire"
        assert len(alert_calls) == 0, (
            f"QUALITY_ALERT handler fired for a UPDATED event — value aliasing bug!\n"
            f"  DATA_PRODUCT_QUALITY_ALERT.value = {EventType.DATA_PRODUCT_QUALITY_ALERT.value}\n"
            f"  DATA_PRODUCT_UPDATED.value        = {EventType.DATA_PRODUCT_UPDATED.value}"
        )
