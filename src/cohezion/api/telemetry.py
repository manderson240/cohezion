import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from cohezion.universe.triune_manifold import TriuneState


logger = logging.getLogger(__name__)

router = APIRouter(tags=["telemetry"])


class ConnectionManager:
    """Manages active WebSocket connections for telemetry."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Telemetry client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Telemetry client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]):
        """Broadcasts telemetry data to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                # We don't remove here to avoid modifying list during iteration
                # disconnect() is handled by the endpoint loop


manager = ConnectionManager()


@router.websocket("/telemetry")
async def telemetry_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time manifold telemetry."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open, client might send heartbeats but primarily we broadcast
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_state(trajectory_id: str, state: TriuneState, coherence: float):
    """
    Utility function to broadcast a state update to all connected clients.

    Args:
        trajectory_id: ID of the simulation journey.
        state: The TriuneState object.
        coherence: The calculated coherence score.
    """
    message = {
        "trajectory_id": trajectory_id,
        "coherence": round(coherence, 4),
        "state": {
            "doer": state.doer.tolist(),
            "thinker": state.thinker.tolist()[:10],  # Truncated for telemetry efficiency
            "knower": state.knower.tolist()[:10],  # Truncated for telemetry efficiency
        },
    }
    await manager.broadcast(message)
