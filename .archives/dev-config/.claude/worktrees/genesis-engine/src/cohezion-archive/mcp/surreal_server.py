"""
SurrealDB MCP Server - Universe node tools.

Provides tools:
- query_nodes: Query universe nodes
- store_node: Store a new node
- search_similar: Vector similarity search
"""

import logging
from typing import Any

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)


logger = logging.getLogger(__name__)


class SurrealMCP:
    """
    MCP server for SurrealDB universe nodes.

    Provides structured access to the 12D physics state database.
    """

    def __init__(self):
        self._client: SurrealClient | None = None

    async def _get_client(self) -> SurrealClient:
        """Lazy-load SurrealDB client."""
        if self._client is None:
            self._client = SurrealClient()
            await self._client.connect()
        return self._client

    async def query_nodes(
        self,
        limit: int = 10,
        filter_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query universe nodes.

        Args:
            limit: Max results
            filter_type: Optional type filter

        Returns:
            List of nodes
        """
        client = await self._get_client()
        nodes = await client.get_all_nodes(limit=limit)

        if filter_type:
            nodes = [n for n in nodes if n.metadata.get("type") == filter_type]

        return [
            {
                "id": n.id,
                "content": n.content[:200] + "..." if len(n.content) > 200 else n.content,
                "physics": n.physics_state.to_dict(),
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in nodes
        ]

    async def store_node(
        self,
        content: str,
        node_type: str = "document",
        physics: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Store a new universe node.

        Args:
            content: Node content
            node_type: Type of node
            physics: Optional physics state overrides

        Returns:
            Created node info
        """
        client = await self._get_client()

        # Create physics state
        physics_state = PhysicsState(**(physics or {}))

        node = UniverseNode(
            content=content,
            physics_state=physics_state,
            metadata={"type": node_type},
        )

        node_id = await client.store_node(node)

        return {
            "id": node_id,
            "content": content[:100],
            "type": node_type,
        }

    async def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search for similar nodes by embedding.

        Args:
            query_embedding: Query vector
            limit: Max results

        Returns:
            Similar nodes with scores
        """
        client = await self._get_client()
        results = await client.search_similar(query_embedding, limit=limit)

        return [
            {
                "id": r["id"],
                "content": r["content"][:200],
                "score": r["score"],
            }
            for r in results
        ]

    async def get_physics_stats(self) -> dict[str, Any]:
        """Get aggregate physics statistics."""
        client = await self._get_client()
        nodes = await client.get_all_nodes(limit=100)

        if not nodes:
            return {"count": 0}

        # Compute averages
        import numpy as np

        physics_arrays = [n.physics_state.to_array() for n in nodes]
        avg = np.mean(physics_arrays, axis=0)

        dim_names = [
            "x",
            "y",
            "z",
            "time",
            "mass",
            "sentiment",
            "complexity",
            "factuality",
            "connectivity",
            "stability",
            "novelty",
            "precipitation",
        ]

        return {
            "count": len(nodes),
            "averages": dict(zip(dim_names, avg.tolist(), strict=False)),
        }

    async def store_learning(
        self,
        learning_id: str,
        title: str,
        content: str,
        pattern: str | None = None,
        score: float = 0.0,
    ) -> dict[str, Any]:
        """
        Store a learning extracted from experience.

        Args:
            learning_id: Unique learning identifier (e.g., "Learning 37")
            title: Short title for the learning
            content: Full learning content
            pattern: Identified pattern or anti-pattern
            score: Confidence/quality score (0.0 to 1.0)

        Returns:
            Created learning node info
        """
        client = await self._get_client()

        # Create physics state with learning-specific values
        physics_state = PhysicsState(
            precipitation=score,
            novelty=0.8,  # Learnings are novel by definition
            logic=score,
        )

        # Generate unique node ID from learning_id
        import hashlib

        node_id = f"learning_{hashlib.sha256(learning_id.encode()).hexdigest()[:12]}"

        node = UniverseNode(
            id=node_id,
            content=content,
            physics_state=physics_state,
            metadata={
                "type": "learning",
                "learning_id": learning_id,
                "title": title,
                "pattern": pattern,
                "score": score,
            },
        )

        node_id = await client.store_node(node)
        logger.info(f"Stored learning {learning_id}: {title}")

        return {
            "id": node_id,
            "learning_id": learning_id,
            "title": title,
            "score": score,
        }

    async def query_learnings(
        self,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Query stored learnings.

        Args:
            limit: Max results
            min_score: Minimum score filter

        Returns:
            List of learnings
        """
        client = await self._get_client()
        nodes = await client.get_all_nodes(limit=limit * 2)  # Over-fetch for filter

        learnings = [
            n for n in nodes if n.metadata.get("type") == "learning" and n.metadata.get("score", 0) >= min_score
        ][:limit]

        return [
            {
                "id": n.id,
                "learning_id": n.metadata.get("learning_id"),
                "title": n.metadata.get("title"),
                "pattern": n.metadata.get("pattern"),
                "score": n.metadata.get("score"),
                "content": n.content[:300] + "..." if len(n.content) > 300 else n.content,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in learnings
        ]

    async def sync_key_learnings(self, markdown_path: str | None = None) -> dict[str, Any]:
        """
        Sync KEY_LEARNINGS.md to SurrealDB.

        Parses the markdown file and stores each learning as a node.

        Args:
            markdown_path: Path to KEY_LEARNINGS.md

        Returns:
            Sync summary with count and any errors
        """
        import re
        from pathlib import Path

        if markdown_path is None:
            markdown_path = "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/KEY_LEARNINGS.md"

        path = Path(markdown_path)
        if not path.exists():
            return {"error": f"File not found: {markdown_path}"}

        content = path.read_text()

        # Parse learnings (pattern: ## Learning N: Title)
        pattern = r"##\s+Learning\s+(\d+)[:\s]+([^\n]+)\n(.*?)(?=##\s+Learning|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        synced = 0
        errors = []

        for num, title, body in matches:
            try:
                learning_id = f"Learning {num}"
                await self.store_learning(
                    learning_id=learning_id,
                    title=title.strip(),
                    content=body.strip()[:2000],  # Truncate if too long
                    score=0.7,  # Default score for manual learnings
                )
                synced += 1
            except Exception as e:
                errors.append(f"{learning_id}: {e!s}")
                logger.error(f"Failed to sync {learning_id}: {e}")

        logger.info(f"Synced {synced} learnings from KEY_LEARNINGS.md")

        return {
            "synced": synced,
            "errors": errors,
            "source": markdown_path,
        }


TOOLS = [
    {
        "name": "query_nodes",
        "description": "Query universe nodes",
        "parameters": {
            "limit": {"type": "integer", "default": 10},
            "filter_type": {"type": "string"},
        },
    },
    {
        "name": "store_node",
        "description": "Store a new universe node",
        "parameters": {
            "content": {"type": "string", "required": True},
            "node_type": {"type": "string", "default": "document"},
            "physics": {"type": "object"},
        },
    },
    {
        "name": "search_similar",
        "description": "Vector similarity search",
        "parameters": {
            "query_embedding": {"type": "array", "required": True},
            "limit": {"type": "integer", "default": 5},
        },
    },
    {
        "name": "store_learning",
        "description": "Store a learning extracted from experience",
        "parameters": {
            "learning_id": {"type": "string", "required": True},
            "title": {"type": "string", "required": True},
            "content": {"type": "string", "required": True},
            "pattern": {"type": "string"},
            "score": {"type": "number", "default": 0.0},
        },
    },
    {
        "name": "query_learnings",
        "description": "Query stored learnings for state awareness",
        "parameters": {
            "limit": {"type": "integer", "default": 20},
            "min_score": {"type": "number", "default": 0.0},
        },
    },
    {
        "name": "sync_key_learnings",
        "description": "Sync KEY_LEARNINGS.md to SurrealDB",
        "parameters": {
            "markdown_path": {"type": "string"},
        },
    },
]

_server: SurrealMCP | None = None


def get_server() -> SurrealMCP:
    global _server
    if _server is None:
        _server = SurrealMCP()
    return _server
