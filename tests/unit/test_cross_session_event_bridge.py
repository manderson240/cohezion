import asyncio
from unittest.mock import AsyncMock

import pytest

from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventBus


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
