"""Repository pattern for database abstraction.

Provides clean interfaces for data access, decoupling business logic
from database implementation details.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UniverseNode:
    """Domain entity for 12D physics state nodes."""

    id: str | None
    agent_id: str
    journey_id: str
    timestamp: datetime
    spatial_x: float
    spatial_y: float
    spatial_z: float
    temporal: float
    physics: float
    biology: float
    logic: float
    quantum: float
    field: float
    control: float
    novelty: float
    precipitation: float
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AgentJourney:
    """Domain entity for agent journey tracking."""

    id: str | None
    agent_name: str
    model: str
    start_time: datetime
    end_time: datetime | None
    status: str
    node_count: int
    metadata: dict[str, Any]


class DBClientProtocol(Protocol):
    """Protocol for database client."""

    async def query(self, sql: str, variables: dict[str, Any] | None = None) -> Any: ...
    async def create(self, table: str, data: dict[str, Any]) -> Any: ...
    async def update(self, thing: str, data: dict[str, Any]) -> Any: ...


class NodeRepository(ABC):
    """Abstract repository for UniverseNode entities."""

    @abstractmethod
    async def get_by_id(self, node_id: str) -> UniverseNode | None: ...

    @abstractmethod
    async def get_by_journey(self, journey_id: str, limit: int = 100) -> list[UniverseNode]: ...

    @abstractmethod
    async def get_by_agent(self, agent_id: str, limit: int = 100) -> list[UniverseNode]: ...

    @abstractmethod
    async def create(self, node: UniverseNode) -> UniverseNode: ...

    @abstractmethod
    async def search_similar(
        self, vector: list[float], threshold: float = 0.9, limit: int = 10
    ) -> list[tuple[UniverseNode, float]]: ...


class SurrealNodeRepository(NodeRepository):
    """SurrealDB implementation of NodeRepository."""

    def __init__(self, client: DBClientProtocol):
        self._client = client

    async def get_by_id(self, node_id: str) -> UniverseNode | None:
        result = await self._client.query(
            "SELECT * FROM universe_nodes WHERE id = $id", {"id": node_id}
        )

        if result and len(result) > 0:
            data = result[0].get("result", [None])[0]
            if data:
                return self._to_entity(data)
        return None

    async def get_by_journey(self, journey_id: str, limit: int = 100) -> list[UniverseNode]:
        result = await self._client.query(
            "SELECT * FROM universe_nodes WHERE journey_id = $journey_id LIMIT $limit",
            {"journey_id": journey_id, "limit": limit},
        )

        nodes = []
        if result and len(result) > 0:
            for row in result[0].get("result", []):
                nodes.append(self._to_entity(row))
        return nodes

    async def get_by_agent(self, agent_id: str, limit: int = 100) -> list[UniverseNode]:
        result = await self._client.query(
            "SELECT * FROM universe_nodes WHERE agent_id = $agent_id LIMIT $limit",
            {"agent_id": agent_id, "limit": limit},
        )

        nodes = []
        if result and len(result) > 0:
            for row in result[0].get("result", []):
                nodes.append(self._to_entity(row))
        return nodes

    async def create(self, node: UniverseNode) -> UniverseNode:
        data = self._to_dict(node)
        result = await self._client.create("universe_nodes", data)

        # Update with returned ID
        if result and len(result) > 0:
            data["id"] = result[0].get("id")
            return self._to_entity(data)
        return node

    async def search_similar(
        self, vector: list[float], threshold: float = 0.9, limit: int = 10
    ) -> list[tuple[UniverseNode, float]]:
        query = """
        SELECT *, vector::similarity::cosine(embedding, $vec) as sim
        FROM universe_nodes
        WHERE embedding <|4|> $vec
        ORDER BY embedding <|4|> $vec ASC
        LIMIT $limit;
        """

        result = await self._client.query(query, {"vec": vector, "limit": limit})

        nodes = []
        if result and len(result) > 0:
            for row in result[0].get("result", []):
                sim = row.get("sim", 0.0)
                if sim >= threshold:
                    nodes.append((self._to_entity(row), sim))
        return nodes

    def _to_entity(self, data: dict[str, Any]) -> UniverseNode:
        """Convert database record to entity."""
        return UniverseNode(
            id=str(data.get("id", "")),
            agent_id=data.get("agent_id", ""),
            journey_id=data.get("journey_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            spatial_x=data.get("spatial_x", 0.0),
            spatial_y=data.get("spatial_y", 0.0),
            spatial_z=data.get("spatial_z", 0.0),
            temporal=data.get("temporal", 0.0),
            physics=data.get("physics", 0.0),
            biology=data.get("biology", 0.0),
            logic=data.get("logic", 0.0),
            quantum=data.get("quantum", 0.0),
            field=data.get("field", 0.0),
            control=data.get("control", 0.0),
            novelty=data.get("novelty", 0.0),
            precipitation=data.get("precipitation", 0.0),
            metadata=data.get("metadata", {}),
        )

    def _to_dict(self, node: UniverseNode) -> dict[str, Any]:
        """Convert entity to database record."""
        return {
            "agent_id": node.agent_id,
            "journey_id": node.journey_id,
            "timestamp": node.timestamp.isoformat(),
            "spatial_x": node.spatial_x,
            "spatial_y": node.spatial_y,
            "spatial_z": node.spatial_z,
            "temporal": node.temporal,
            "physics": node.physics,
            "biology": node.biology,
            "logic": node.logic,
            "quantum": node.quantum,
            "field": node.field,
            "control": node.control,
            "novelty": node.novelty,
            "precipitation": node.precipitation,
            "metadata": node.metadata,
        }


class JourneyRepository(ABC):
    """Abstract repository for AgentJourney entities."""

    @abstractmethod
    async def get_by_id(self, journey_id: str) -> AgentJourney | None: ...

    @abstractmethod
    async def get_by_agent(self, agent_name: str, limit: int = 100) -> list[AgentJourney]: ...

    @abstractmethod
    async def create(self, journey: AgentJourney) -> AgentJourney: ...

    @abstractmethod
    async def update_status(
        self, journey_id: str, status: str, metadata: dict[str, Any] | None = None
    ) -> AgentJourney | None: ...


class SurrealJourneyRepository(JourneyRepository):
    """SurrealDB implementation of JourneyRepository."""

    def __init__(self, client: DBClientProtocol):
        self._client = client

    async def get_by_id(self, journey_id: str) -> AgentJourney | None:
        result = await self._client.query(
            "SELECT * FROM agent_journeys WHERE id = $id", {"id": journey_id}
        )

        if result and len(result) > 0:
            data = result[0].get("result", [None])[0]
            if data:
                return self._to_entity(data)
        return None

    async def get_by_agent(self, agent_name: str, limit: int = 100) -> list[AgentJourney]:
        result = await self._client.query(
            "SELECT * FROM agent_journeys WHERE agent_name = $agent_name LIMIT $limit",
            {"agent_name": agent_name, "limit": limit},
        )

        journeys = []
        if result and len(result) > 0:
            for row in result[0].get("result", []):
                journeys.append(self._to_entity(row))
        return journeys

    async def create(self, journey: AgentJourney) -> AgentJourney:
        data = self._to_dict(journey)
        result = await self._client.create("agent_journeys", data)

        if result and len(result) > 0:
            data["id"] = result[0].get("id")
            return self._to_entity(data)
        return journey

    async def update_status(
        self, journey_id: str, status: str, metadata: dict[str, Any] | None = None
    ) -> AgentJourney | None:
        updates = {"status": status}
        if metadata:
            updates["metadata"] = metadata

        result = await self._client.update(journey_id, updates)

        if result:
            return self._to_entity(result)
        return None

    def _to_entity(self, data: dict[str, Any]) -> AgentJourney:
        end_time = data.get("end_time")
        return AgentJourney(
            id=str(data.get("id", "")),
            agent_name=data.get("agent_name", ""),
            model=data.get("model", ""),
            start_time=datetime.fromisoformat(data.get("start_time", datetime.now().isoformat())),
            end_time=datetime.fromisoformat(end_time) if end_time else None,
            status=data.get("status", "unknown"),
            node_count=data.get("node_count", 0),
            metadata=data.get("metadata", {}),
        )

    def _to_dict(self, journey: AgentJourney) -> dict[str, Any]:
        result = {
            "agent_name": journey.agent_name,
            "model": journey.model,
            "start_time": journey.start_time.isoformat(),
            "status": journey.status,
            "node_count": journey.node_count,
            "metadata": journey.metadata,
        }
        if journey.end_time:
            result["end_time"] = journey.end_time.isoformat()
        return result


# Repository factory
class RepositoryFactory:
    """Factory for creating repository instances."""

    def __init__(self, client: DBClientProtocol):
        self._client = client
        self._node_repo: NodeRepository | None = None
        self._journey_repo: JourneyRepository | None = None

    def node_repository(self) -> NodeRepository:
        if self._node_repo is None:
            self._node_repo = SurrealNodeRepository(self._client)
        return self._node_repo

    def journey_repository(self) -> JourneyRepository:
        if self._journey_repo is None:
            self._journey_repo = SurrealJourneyRepository(self._client)
        return self._journey_repo


# Global factory instance
_repository_factory: RepositoryFactory | None = None


def get_repository_factory(client: DBClientProtocol | None = None) -> RepositoryFactory:
    """Get or create repository factory."""
    global _repository_factory
    if _repository_factory is None and client is not None:
        _repository_factory = RepositoryFactory(client)
    if _repository_factory is None:
        raise RuntimeError("RepositoryFactory not initialized")
    return _repository_factory
