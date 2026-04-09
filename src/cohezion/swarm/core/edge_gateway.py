"""Gateway for registering and managing external Edge AI nodes (e.g. Pixel devices).
Allows the swarm to offload sensing and classification to mobile hardware
via an asynchronous API bridge.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel


logger = logging.getLogger(__name__)


@dataclass
class EdgeNode:
    """State of a registered mobile edge device."""

    node_id: str
    device_model: str
    model_name: str
    endpoint: str
    status: str = "active"
    last_seen: float = 0.0
    capabilities: list[str] = field(default_factory=list)


class RegistrationRequest(BaseModel):
    """Payload for edge node registration."""

    device_model: str
    model_name: str
    endpoint: str
    capabilities: list[str] = []


class EdgeGateway:
    """Manages a registry of mobile edge devices for distributed inference."""

    def __init__(self):
        self._nodes: dict[str, EdgeNode] = {}

    async def register_node(self, req: RegistrationRequest) -> str:
        """Registers a new edge node and returns a unique node_id."""
        node_id = str(uuid.uuid4())
        self._nodes[node_id] = EdgeNode(
            node_id=node_id,
            device_model=req.device_model,
            model_name=req.model_name,
            endpoint=req.endpoint,
            capabilities=req.capabilities,
        )
        logger.info("Registered edge node %s (%s) at %s", node_id, req.device_model, req.endpoint)
        return node_id

    async def get_node(self, node_id: str) -> EdgeNode | None:
        """Retrieve node state by ID."""
        return self._nodes.get(node_id)

    async def list_active_nodes(self) -> list[EdgeNode]:
        """Returns all currently active edge nodes."""
        return [n for n in self._nodes.values() if n.status == "active"]

    async def deregister_node(self, node_id: str) -> bool:
        """Removes a node from the registry."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False


# Singleton instance for the swarm
_gateway_instance: EdgeGateway | None = None


def get_edge_gateway() -> EdgeGateway:
    """Get the singleton instance of the EdgeGateway."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = EdgeGateway()
    return _gateway_instance
