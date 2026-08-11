import pytest
import asyncio
from unittest.mock import AsyncMock
from cohezion.core.event_bus import EventBus, Event
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge

@pytest.mark.asyncio
async def test_cross_session_event_bridge_initialization_and_publish():
    bus = EventBus()
    await bus.start()

    mock_surreal = AsyncMock()
    mock_surreal.query.return_value = [{"result": [{"type": "AGENT_COMPLETE", "source": "agent_alpha"}]}]

    bridge = CrossSessionEventBridge(event_bus=bus, session_id="session_test_101", surreal_client=mock_surreal)
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
