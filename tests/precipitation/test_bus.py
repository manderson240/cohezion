"""Tests for PrecipitationBus fan-out and lifecycle."""

from __future__ import annotations

import asyncio

import pytest

from cohezion.precipitation.bus import PrecipitationBus, get_bus, set_bus
from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind


def _mk(kind: PrecipitationKind = PrecipitationKind.WITNESS_MARK) -> PrecipitationEvent:
    return PrecipitationEvent(kind=kind, universe_id="u1", coherence=0.6)


@pytest.mark.asyncio
async def test_bus_delivers_to_kind_and_wildcard() -> None:
    bus = PrecipitationBus()
    await bus.start()
    witness_events: list[PrecipitationEvent] = []
    all_events: list[PrecipitationEvent] = []

    bus.subscribe(witness_events.append, kind=PrecipitationKind.WITNESS_MARK)
    bus.subscribe(all_events.append, kind=None)

    await bus.aemit(_mk(PrecipitationKind.WITNESS_MARK))
    await bus.aemit(_mk(PrecipitationKind.COSMOGONY_PHASE))
    await bus.flush()

    assert len(witness_events) == 1
    assert len(all_events) == 2
    await bus.stop()


@pytest.mark.asyncio
async def test_bus_survives_sink_exception() -> None:
    bus = PrecipitationBus()
    await bus.start()
    delivered: list[PrecipitationEvent] = []

    def bad_sink(event: PrecipitationEvent) -> None:
        raise RuntimeError("sink blew up")

    bus.subscribe(bad_sink, kind=None)
    bus.subscribe(delivered.append, kind=None)

    await bus.aemit(_mk())
    await bus.aemit(_mk())
    await bus.flush()

    assert len(delivered) == 2
    assert bus.stats["failures"] >= 2
    await bus.stop()


@pytest.mark.asyncio
async def test_bus_supports_async_subscribers() -> None:
    bus = PrecipitationBus()
    await bus.start()
    seen: list[PrecipitationEvent] = []

    async def async_sink(event: PrecipitationEvent) -> None:
        await asyncio.sleep(0)
        seen.append(event)

    bus.subscribe(async_sink, kind=None)
    await bus.aemit(_mk())
    await bus.flush()
    assert len(seen) == 1
    await bus.stop()


def test_sync_emit_without_loop_dispatches_sync_subscribers() -> None:
    """Plain Python code (no asyncio) must still get sync subscribers invoked."""
    bus = PrecipitationBus()
    delivered: list[PrecipitationEvent] = []
    bus.subscribe(delivered.append, kind=None)

    bus.emit(_mk())
    bus.emit(_mk())

    assert len(delivered) == 2


def test_global_bus_is_singleton() -> None:
    set_bus(None)
    first = get_bus()
    second = get_bus()
    assert first is second
    set_bus(None)  # reset for later tests


def test_set_bus_allows_test_isolation() -> None:
    set_bus(None)
    original = get_bus()
    injected = PrecipitationBus()
    set_bus(injected)
    assert get_bus() is injected
    set_bus(None)  # back to a fresh default
    assert get_bus() is not original
    assert get_bus() is not injected
