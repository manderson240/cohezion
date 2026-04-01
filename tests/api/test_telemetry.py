import pytest
import torch
from fastapi.testclient import TestClient

from cohezion.api import app


@pytest.mark.asyncio
async def test_telemetry_websocket_connection():
    """Test that a client can connect to the telemetry websocket."""
    client = TestClient(app)
    with client.websocket_connect("/telemetry") as websocket:
        # Initial connection should be successful
        assert websocket is not None

@pytest.mark.asyncio
async def test_telemetry_broadcast():
    """Test that the engine can broadcast state to the websocket."""
    from cohezion.api.telemetry import broadcast_state
    from cohezion.universe.triune_manifold import TriuneState
    
    client = TestClient(app)
    with client.websocket_connect("/telemetry") as websocket:
        # Create a dummy state
        state = TriuneState(
            doer=torch.ones(12),
            thinker=torch.zeros(512),
            knower=torch.zeros(2048)
        )
        
        # Manually trigger a broadcast for testing
        await broadcast_state(trajectory_id="test_1", state=state, coherence=0.5)
        
        # Receive the data
        data = websocket.receive_json()
        assert data["trajectory_id"] == "test_1"
        assert data["coherence"] == 0.5
        assert len(data["state"]["doer"]) == 12
        assert len(data["state"]["thinker"]) == 10
        assert len(data["state"]["knower"]) == 10
