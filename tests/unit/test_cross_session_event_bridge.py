import asyncio
from unittest.mock import AsyncMock

import pytest

from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventBus
from cohezion.core.persistence.surreal_client import SurrealClient


@pytest.mark.asyncio
async def test_cross_session_event_bridge_initialization_and_publish():
    bus = EventBus()
    await bus.start()

    mock_surreal = AsyncMock()
    mock_surreal.query.return_value = [
        {"result": [{"type": "AGENT_COMPLETE", "source": "agent_alpha"}]}
    ]

    bridge = CrossSessionEventBridge(
        event_bus=bus, session_id="session_test_101", surreal_client=mock_surreal
    )
    await bridge.initialize()

    evt = Event.agent_start("agent_alpha", model="deepseek-r1")
    await bus.publish(evt)
    await asyncio.sleep(0.05)

    # Verify SurrealDB query was called
    assert mock_surreal.query.called

    events = await bridge.fetch_cross_session_events()
    assert len(events) == 1
    assert events[0]["source"] == "agent_alpha"

    await bus.stop()


# --- publish_and_persist: the SYNC one-shot path used by 5 production callers ---
# Regression guard (2026-09-04): publish_and_persist only called publish_sync(),
# which merely enqueues. With no running bus nothing drains the queue, so the
# event reached neither a handler nor SurrealDB -- yet it returned True.


def _bridge_with_mock(mock_surreal):
    return CrossSessionEventBridge(
        event_bus=EventBus(), session_id="s_sync_test", surreal_client=mock_surreal
    )


def test_publish_and_persist_writes_to_surreal_without_a_running_bus():
    """CONSUMPTION: the sync path must reach the database, not just a queue."""
    mock_surreal = AsyncMock()
    mock_surreal.query.return_value = [{"result": []}]
    bridge = _bridge_with_mock(mock_surreal)

    ok = bridge.publish_and_persist(Event.agent_start("agent_sync", model="m"))

    assert mock_surreal.query.called, "event never reached SurrealDB"
    assert ok is True


def test_publish_and_persist_reports_false_when_the_backend_fails():
    """DISCRIMINATING: a backend failure must not be reported as success."""
    mock_surreal = AsyncMock()
    mock_surreal.query.side_effect = RuntimeError("surreal down")
    bridge = _bridge_with_mock(mock_surreal)

    ok = bridge.publish_and_persist(Event.agent_start("agent_sync", model="m"))

    assert ok is False, "backend failure reported as success"


def test_record_id_is_deterministic_so_upsert_is_idempotent():
    """At-least-once delivery must not create duplicate event_log rows."""
    bridge = _bridge_with_mock(AsyncMock())
    evt = Event.agent_start("agent_sync", model="m")
    assert bridge._record_id(evt) == bridge._record_id(evt)


# --- in-loop path (adversarial review, 2026-09-18) ---


@pytest.mark.asyncio
async def test_in_loop_publish_and_persist_refuses_when_bus_not_running():
    """An event put_nowait into an undrained queue is the original defect."""
    bridge = _bridge_with_mock(AsyncMock())
    assert not bridge.event_bus._running

    assert bridge.publish_and_persist(Event.agent_start("a", model="m")) is False


@pytest.mark.asyncio
async def test_in_loop_persist_task_is_retained_and_failure_is_logged(caplog):
    mock_surreal = AsyncMock()
    mock_surreal.query.side_effect = RuntimeError("surreal down")
    bridge = _bridge_with_mock(mock_surreal)
    await bridge.event_bus.start()
    try:
        with caplog.at_level("WARNING"):
            ok = bridge.publish_and_persist(Event.agent_start("a", model="m"))
            assert ok is True  # dispatched; persistence is scheduled
            assert len(bridge._pending_persist) == 1, "persist task not retained"
            for _ in range(20):
                await asyncio.sleep(0)
                if not bridge._pending_persist:
                    break
        assert bridge._pending_persist == set()
        assert "Failed to persist" in caplog.text
    finally:
        await bridge.event_bus.stop()


# --- known-broken persistence must be loud and must not report success (2026-09-21) ---
# Measured: a session without SurrealDB credentials (client refuses root/root) got True from
# publish_and_persist on every call while nothing reached event_log.

_REFUSED = RuntimeError("Refusing to connect to SurrealDB: no credentials")


@pytest.mark.asyncio
async def test_initialize_detects_unpersistable_backend_loudly(caplog):
    mock_surreal = AsyncMock()
    mock_surreal.query.side_effect = _REFUSED
    bridge = _bridge_with_mock(mock_surreal)
    with caplog.at_level("ERROR"):
        await bridge.initialize()
    assert bridge.persistence_error is not None
    assert "CANNOT persist" in caplog.text


@pytest.mark.asyncio
async def test_in_loop_publish_reports_false_while_persistence_is_known_broken():
    """DISCRIMINATING: the exact 2026-09-21 case. The old code returned True here."""
    mock_surreal = AsyncMock()
    mock_surreal.query.side_effect = _REFUSED
    bridge = _bridge_with_mock(mock_surreal)
    await bridge.event_bus.start()
    try:
        await bridge.initialize()
        assert bridge.publish_and_persist(Event.agent_start("a", model="m")) is False
    finally:
        await bridge.event_bus.stop()


@pytest.mark.asyncio
async def test_healthy_backend_still_reports_true_and_clears_after_recovery():
    mock_surreal = AsyncMock()
    mock_surreal.query.side_effect = [_REFUSED, [{"result": []}], [{"result": []}]]
    bridge = _bridge_with_mock(mock_surreal)
    await bridge.initialize()  # probe fails
    assert bridge.persistence_error is not None
    assert await bridge._persist(Event.agent_start("a", model="m")) is True  # backend back
    assert bridge.persistence_error is None


@pytest.mark.asyncio
async def test_in_loop_persist_task_that_raises_is_logged_not_swallowed(caplog):
    bridge = _bridge_with_mock(AsyncMock())
    bridge._persist = AsyncMock(side_effect=RuntimeError("boom"))
    await bridge.event_bus.start()
    try:
        with caplog.at_level("WARNING"):
            assert bridge.publish_and_persist(Event.agent_start("a", model="m")) is True
            for _ in range(20):
                await asyncio.sleep(0)
                if not bridge._pending_persist:
                    break
        assert "persist task failed" in caplog.text
        assert "boom" in caplog.text
    finally:
        await bridge.event_bus.stop()


# --- a silent InMemoryStore fallback is not persistence (adversarial review 2026-09-21) ---
# SurrealClient.connect() falls back to InMemoryStore when the server is unreachable. The
# RETURN 1 probe and every UPSERT then "succeed" against process-local memory, so the bridge
# reported True while nothing reached event_log.


def _dead_port_client(monkeypatch):
    from cohezion.core.persistence import surreal_client as sc

    # Credentials present (the pre-e444a980b failure was their ABSENCE); the server is not.
    monkeypatch.setattr(sc, "_resolve_surreal_credentials", lambda: ("tester", "not-a-secret"))
    return SurrealClient(url="ws://127.0.0.1:1/rpc")


def test_sync_publish_reports_false_when_client_fell_back_to_memory(monkeypatch):
    """DISCRIMINATING: the old bridge returned True and left persistence_error None."""
    bridge = CrossSessionEventBridge(
        event_bus=EventBus(),
        session_id="s_dead_port",
        surreal_client=_dead_port_client(monkeypatch),
    )
    assert bridge.publish_and_persist(Event.agent_start("a", model="m")) is False
    assert bridge.persistence_error is not None
    assert "InMemoryStore" in bridge.persistence_error


@pytest.mark.asyncio
async def test_initialize_probe_detects_memory_fallback(monkeypatch):
    bridge = CrossSessionEventBridge(
        event_bus=EventBus(),
        session_id="s_dead_probe",
        surreal_client=_dead_port_client(monkeypatch),
    )
    await bridge.initialize()
    assert bridge.persistence_error is not None
    assert "InMemoryStore" in bridge.persistence_error


@pytest.mark.asyncio
async def test_persist_timeout_records_persistence_error(monkeypatch):
    from cohezion.core import cross_session_event_bridge as mod

    async def _hang(*_a, **_k):
        await asyncio.sleep(10)

    mock_surreal = AsyncMock()
    mock_surreal.query.side_effect = _hang
    monkeypatch.setattr(mod, "_EVENT_HANDLER_TIMEOUT_S", 0.05)
    bridge = _bridge_with_mock(mock_surreal)
    assert await bridge._persist(Event.agent_start("a", model="m")) is False
    assert bridge.persistence_error is not None
