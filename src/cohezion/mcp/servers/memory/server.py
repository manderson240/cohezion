"""Memory MCP Server - Knowledge graph with Entity-Relation-Observation model.

Port: 8366
Features:
- Entity management (agents, concepts, objects)
- Relation tracking (interactions, dependencies)
- Observations storage (facts, events)
- Graph traversal queries
- Cross-session persistence

Based on MCP Reference Memory Server with FLUME integration.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aiohttp import web

from cohezion.security.credentials import get_credentials


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8366"))
# Primary: Vault Warden, Fallback: Environment
SURREAL_URL = (
    get_credentials().get_secret("COHEZION_SURREAL_URL", env_var="SURREAL_URL")
    or "ws://localhost:8000/rpc"
)


@dataclass
class Entity:
    """Knowledge graph entity."""

    name: str
    entity_type: str  # "agent", "concept", "object", etc.
    observations: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entityType": self.entity_type,
            "observations": self.observations,
            "createdAt": self.created_at,
        }


@dataclass
class Relation:
    """Relationship between entities."""

    from_entity: str
    to_entity: str
    relation_type: str  # "depends_on", "interacts_with", "contains", etc.
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "from": self.from_entity,
            "to": self.to_entity,
            "relationType": self.relation_type,
            "createdAt": self.created_at,
        }


class MemoryGraph:
    """In-memory knowledge graph with SurrealDB persistence."""

    def __init__(self):
        self.entities: dict[str, Entity] = {}
        self.relations: list[Relation] = []
        self._surreal: Any = None

    async def _get_surreal(self):
        """Get or create SurrealDB connection."""
        if self._surreal is None:
            try:
                from surrealdb import AsyncSurreal

                client = AsyncSurreal(SURREAL_URL)
                await client.connect()
                await client.signin(
                    {
                        "username": os.getenv("SURREAL_USER", "root"),
                        "password": os.getenv("SURREAL_PASSWORD", "root"),
                    }
                )
                await client.use("bmad", "memory")
                self._surreal = client
                logger.info("Connected to SurrealDB at %s (bmad/memory)", SURREAL_URL)
            except Exception as e:
                logger.warning("SurrealDB not available: %s", e)
                self._surreal = None
        return self._surreal

    async def load_from_surreal(self) -> None:
        """Load existing entities and relations from SurrealDB into memory on startup."""
        db = await self._get_surreal()
        if db is None:
            return
        try:
            entity_rows = await db.query("SELECT * FROM memory_entities")
            rows = entity_rows[0].get("result", []) if entity_rows else []
            for row in rows:
                entity = Entity(
                    name=row["name"],
                    entity_type=row["entity_type"],
                    observations=row.get("observations", []),
                    created_at=row.get("created_at", datetime.utcnow().isoformat()),
                )
                self.entities[entity.name] = entity
            logger.info("Loaded %d entities from SurrealDB", len(rows))

            relation_rows = await db.query("SELECT * FROM memory_relations")
            rows = relation_rows[0].get("result", []) if relation_rows else []
            for row in rows:
                relation = Relation(
                    from_entity=row["from_entity"],
                    to_entity=row["to_entity"],
                    relation_type=row["relation_type"],
                    created_at=row.get("created_at", datetime.utcnow().isoformat()),
                )
                self.relations.append(relation)
            logger.info("Loaded %d relations from SurrealDB", len(rows))
        except Exception as e:
            logger.warning("Failed to load from SurrealDB: %s", e)

    async def create_entity(self, name: str, entity_type: str) -> Entity:
        """Create new entity and persist to SurrealDB."""
        entity = Entity(name=name, entity_type=entity_type)
        self.entities[name] = entity
        logger.debug(
            "Created entity: %s (%s)", name.replace("\n", " "), entity_type.replace("\n", " ")
        )
        db = await self._get_surreal()
        if db is not None:
            try:
                await db.create(
                    f"memory_entities:{name}",
                    {
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "observations": entity.observations,
                        "created_at": entity.created_at,
                    },
                )
            except Exception as e:
                logger.warning("Failed to persist entity to SurrealDB: %s", e)
        return entity

    def get_entity(self, name: str) -> Entity | None:
        """Get entity by name."""
        return self.entities.get(name)

    async def add_observation(self, entity_name: str, observation: str) -> bool:
        """Add observation to entity and persist to SurrealDB."""
        entity = self.entities.get(entity_name)
        if entity:
            entity.observations.append(observation)
            logger.debug("Added observation to %s", entity_name.replace("\n", " "))
            db = await self._get_surreal()
            if db is not None:
                try:
                    await db.merge(
                        f"memory_entities:{entity_name}",
                        {"observations": entity.observations},
                    )
                except Exception as e:
                    logger.warning("Failed to persist observation to SurrealDB: %s", e)
            return True
        return False

    async def create_relation(
        self, from_entity: str, to_entity: str, relation_type: str
    ) -> bool:
        """Create relation between entities and persist to SurrealDB."""
        if from_entity not in self.entities or to_entity not in self.entities:
            return False

        relation = Relation(
            from_entity=from_entity, to_entity=to_entity, relation_type=relation_type
        )
        self.relations.append(relation)
        logger.debug(
            "Created relation: %s -%s-> %s",
            from_entity.replace("\n", " "),
            relation_type.replace("\n", " "),
            to_entity.replace("\n", " "),
        )
        db = await self._get_surreal()
        if db is not None:
            try:
                rel_id = f"{from_entity}__{relation_type}__{to_entity}"
                await db.create(
                    f"memory_relations:{rel_id}",
                    {
                        "from_entity": relation.from_entity,
                        "to_entity": relation.to_entity,
                        "relation_type": relation.relation_type,
                        "created_at": relation.created_at,
                    },
                )
            except Exception as e:
                logger.warning("Failed to persist relation to SurrealDB: %s", e)
        return True

    def get_related(self, entity_name: str, relation_type: str | None = None) -> list[str]:
        """Get related entities."""
        related = []
        for rel in self.relations:
            if rel.from_entity == entity_name:
                if relation_type is None or rel.relation_type == relation_type:
                    related.append(rel.to_entity)
            elif rel.to_entity == entity_name:
                if relation_type is None or rel.relation_type == relation_type:
                    related.append(rel.from_entity)
        return list(set(related))  # Remove duplicates

    def search_entities(self, query: str) -> list[Entity]:
        """Search entities by name or observation content."""
        results = []
        query_lower = query.lower()

        for entity in self.entities.values():
            # Check name
            if query_lower in entity.name.lower():
                results.append(entity)
                continue

            # Check observations
            for obs in entity.observations:
                if query_lower in obs.lower():
                    results.append(entity)
                    break

        return results

    def to_dict(self) -> dict:
        """Export graph as dict."""
        return {
            "entities": {name: e.to_dict() for name, e in self.entities.items()},
            "relations": [r.to_dict() for r in self.relations],
        }


# Global graph instance
_graph: MemoryGraph | None = None


def get_graph() -> MemoryGraph:
    """Get or create memory graph."""
    global _graph
    if _graph is None:
        _graph = MemoryGraph()
    return _graph


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "memory",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    graph = get_graph()
    return web.json_response(
        {
            "name": "Memory MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "model": "ERO (Entity-Relation-Observation)",
            "stats": {
                "entities": len(graph.entities),
                "relations": len(graph.relations),
            },
            "tools": [
                "memory_create_entity",
                "memory_get_entity",
                "memory_add_observation",
                "memory_create_relation",
                "memory_search",
                "memory_get_related",
                "memory_export",
            ],
        }
    )


@routes.post("/tools/memory_create_entity")
async def tool_create_entity(request: web.Request) -> web.Response:
    """Create new entity."""
    try:
        data = await request.json()
        name = data.get("name", "")
        entity_type = data.get("entityType", "concept")

        if not name:
            return web.json_response({"error": "name is required"}, status=400)

        graph = get_graph()

        # Check if exists
        if name in graph.entities:
            return web.json_response(
                {
                    "tool": "memory_create_entity",
                    "status": "exists",
                    "entity": graph.entities[name].to_dict(),
                }
            )

        entity = await graph.create_entity(name, entity_type)

        return web.json_response(
            {
                "tool": "memory_create_entity",
                "status": "created",
                "entity": entity.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Create entity failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/memory_get_entity")
async def tool_get_entity(request: web.Request) -> web.Response:
    """Get entity details."""
    try:
        data = await request.json()
        name = data.get("name", "")

        if not name:
            return web.json_response({"error": "name is required"}, status=400)

        graph = get_graph()
        entity = graph.get_entity(name)

        if entity:
            # Get related entities
            related = graph.get_related(name)

            return web.json_response(
                {
                    "tool": "memory_get_entity",
                    "found": True,
                    "entity": entity.to_dict(),
                    "relatedEntities": related,
                }
            )
        else:
            return web.json_response(
                {
                    "tool": "memory_get_entity",
                    "found": False,
                    "name": name,
                },
                status=404,
            )
    except Exception as e:
        logger.exception("Get entity failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/memory_add_observation")
async def tool_add_observation(request: web.Request) -> web.Response:
    """Add observation to entity."""
    try:
        data = await request.json()
        entity_name = data.get("entityName", "")
        observation = data.get("observation", "")

        if not entity_name or not observation:
            return web.json_response(
                {"error": "entityName and observation are required"}, status=400
            )

        graph = get_graph()
        success = await graph.add_observation(entity_name, observation)

        if success:
            return web.json_response(
                {
                    "tool": "memory_add_observation",
                    "status": "added",
                    "entityName": entity_name,
                    "observationCount": len(graph.entities[entity_name].observations),
                }
            )
        else:
            return web.json_response({"error": f"Entity not found: {entity_name}"}, status=404)
    except Exception as e:
        logger.exception("Add observation failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/memory_create_relation")
async def tool_create_relation(request: web.Request) -> web.Response:
    """Create relation between entities."""
    try:
        data = await request.json()
        from_entity = data.get("from", "")
        to_entity = data.get("to", "")
        relation_type = data.get("relationType", "relates_to")

        if not from_entity or not to_entity:
            return web.json_response({"error": "from and to are required"}, status=400)

        graph = get_graph()
        success = await graph.create_relation(from_entity, to_entity, relation_type)

        if success:
            return web.json_response(
                {
                    "tool": "memory_create_relation",
                    "status": "created",
                    "from": from_entity,
                    "to": to_entity,
                    "relationType": relation_type,
                }
            )
        else:
            return web.json_response({"error": "One or both entities not found"}, status=404)
    except Exception as e:
        logger.exception("Create relation failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/memory_search")
async def tool_search(request: web.Request) -> web.Response:
    """Search entities."""
    try:
        data = await request.json()
        query = data.get("query", "")

        if not query:
            return web.json_response({"error": "query is required"}, status=400)

        graph = get_graph()
        results = graph.search_entities(query)

        return web.json_response(
            {
                "tool": "memory_search",
                "query": query,
                "count": len(results),
                "entities": [e.to_dict() for e in results],
            }
        )
    except Exception as e:
        logger.exception("Search failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/memory_get_related")
async def tool_get_related(request: web.Request) -> web.Response:
    """Get related entities."""
    try:
        data = await request.json()
        entity_name = data.get("entityName", "")
        relation_type = data.get("relationType")  # Optional

        if not entity_name:
            return web.json_response({"error": "entityName is required"}, status=400)

        graph = get_graph()
        related = graph.get_related(entity_name, relation_type)

        # Get details of related entities
        related_details = []
        for name in related:
            entity = graph.get_entity(name)
            if entity:
                related_details.append(entity.to_dict())

        return web.json_response(
            {
                "tool": "memory_get_related",
                "entityName": entity_name,
                "relationType": relation_type,
                "count": len(related),
                "related": related_details,
            }
        )
    except Exception as e:
        logger.exception("Get related failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/memory_export")
async def tool_export(request: web.Request) -> web.Response:
    """Export entire memory graph."""
    try:
        graph = get_graph()

        return web.json_response(
            {
                "tool": "memory_export",
                "graph": graph.to_dict(),
                "stats": {
                    "entityCount": len(graph.entities),
                    "relationCount": len(graph.relations),
                },
            }
        )
    except Exception as e:
        logger.exception("Export failed")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance for import
app = create_app()


async def main():
    """Run the Memory MCP Server."""
    graph = get_graph()
    await graph.load_from_surreal()  # Restore persisted state on startup

    logger.info(f"Starting Memory MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ Memory MCP Server running on http://localhost:{MCP_PORT}")
    logger.info("   Model: Entity-Relation-Observation (ERO)")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Memory MCP Server stopped")
