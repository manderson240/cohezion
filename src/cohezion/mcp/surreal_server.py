"""
SurrealDB MCP Server - Universe node tools.

Provides tools:
- query_nodes: Query universe nodes
- store_node: Store a new node
- search_similar: Vector similarity search
"""

import logging
from typing import Any

from cohezion.db.surreal_client import SurrealClient, PhysicsState, UniverseNode

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
        
        dim_names = ["x", "y", "z", "time", "mass", "sentiment", 
                     "complexity", "factuality", "connectivity", 
                     "stability", "novelty", "coherence"]
        
        return {
            "count": len(nodes),
            "averages": dict(zip(dim_names, avg.tolist())),
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
]

_server: SurrealMCP | None = None

def get_server() -> SurrealMCP:
    global _server
    if _server is None:
        _server = SurrealMCP()
    return _server
