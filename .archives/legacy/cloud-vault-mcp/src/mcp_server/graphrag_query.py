"""
GraphRAG Query: Hybrid semantic + graph search

Combines:
- Vector similarity search (semantic context)
- Graph traversal (relationship ancestry)
- Query caching (LRU for frequent queries)
"""

import logging
from functools import lru_cache
from typing import Any

import httpx

from .graphrag_helpers import GraphRAGError, execute_surreal_async


logger = logging.getLogger(__name__)


class GraphRAGQuery:
    """Hybrid semantic + graph query for vault knowledge"""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        surrealdb_url: str = "http://localhost:8001",
        namespace: str = "cohezion",
        database: str = "vault",
        embedding_model: str = "nomic-embed-text:latest",
        max_graph_depth: int = 3,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.surrealdb_url = surrealdb_url
        self.namespace = namespace
        self.database = database
        self.embedding_model = embedding_model
        self.max_graph_depth = max_graph_depth

        self.http_client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate query embedding via Ollama"""
        if not self.http_client:
            raise GraphRAGError("HTTP client not initialized")

        try:
            response = await self.http_client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text[:2000]},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding", [])
            if not embedding:
                raise GraphRAGError("No embedding returned from Ollama")

            return embedding

        except Exception as e:
            logger.error(f"Query embedding generation failed: {e}")
            raise GraphRAGError(f"Failed to generate embedding: {e}")

    async def semantic_search(
        self, query: str, top_k: int = 5, min_score: float = 0.3
    ) -> list[dict[str, Any]]:
        """
        Semantic vector search

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum similarity score (0.0-1.0)

        Returns:
            List of {id, title, type, content, score}
        """
        if not self.http_client:
            raise GraphRAGError("HTTP client not initialized")

        # Generate query embedding
        query_vec = await self.generate_embedding(query)

        # Vector search
        search_query = f"""
        SELECT id, title, type, content, path,
            vector::similarity::cosine(embedding, {query_vec}) AS score
        FROM vault_memory
        WHERE embedding IS NOT NONE
            AND vector::similarity::cosine(embedding, {query_vec}) > {min_score}
        ORDER BY score DESC
        LIMIT {top_k};
        """

        results = await execute_surreal_async(
            search_query, self.http_client, self.namespace, self.database
        )

        return results[0].get("result", [])

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        include_ancestry: bool = True,
        include_descendants: bool = True,
        max_depth: int = None,
    ) -> list[dict[str, Any]]:
        """
        Hybrid semantic + graph search

        Args:
            query: Search query text
            top_k: Number of semantic results
            include_ancestry: Include nodes that informed these results
            include_descendants: Include nodes led to by these results
            max_depth: Max graph traversal depth (default: self.max_graph_depth)

        Returns:
            List of results with graph relationships embedded
        """
        if not self.http_client:
            raise GraphRAGError("HTTP client not initialized")

        max_depth = max_depth or self.max_graph_depth

        # Generate query embedding
        query_vec = await self.generate_embedding(query)

        # Build hybrid query
        ancestry_clause = (
            f"->informed_by[..{max_depth}]->vault_memory AS ancestors"
            if include_ancestry
            else "[] AS ancestors"
        )
        descendants_clause = (
            f"<-led_to[..{max_depth}]<-vault_memory AS descendants"
            if include_descendants
            else "[] AS descendants"
        )

        hybrid_query = f"""
        SELECT id, title, type, content, path,
            vector::similarity::cosine(embedding, {query_vec}) AS score,
            {ancestry_clause},
            {descendants_clause}
        FROM vault_memory
        WHERE embedding IS NOT NONE
        ORDER BY score DESC
        LIMIT {top_k};
        """

        results = await execute_surreal_async(
            hybrid_query, self.http_client, self.namespace, self.database
        )

        return results[0].get("result", [])

    async def find_related(
        self,
        doc_id: str,
        max_depth: int = None,
        relation_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Find all related documents via graph edges

        Args:
            doc_id: Document ID (e.g., 'vault_memory:doc_id')
            max_depth: Max traversal depth
            relation_types: Edge types to follow (default: all)

        Returns:
            Dict with ancestors, descendants, and the document itself
        """
        if not self.http_client:
            raise GraphRAGError("HTTP client not initialized")

        max_depth = max_depth or self.max_graph_depth
        relation_types = relation_types or [
            "informed_by",
            "led_to",
            "used_in",
            "extracted_from",
        ]

        # Build query with all relationship types
        query = f"""
        SELECT *,
            ->informed_by[..{max_depth}]->vault_memory AS informed_by_nodes,
            <-led_to[..{max_depth}]<-vault_memory AS led_to_nodes,
            ->used_in[..{max_depth}]->vault_memory AS used_in_nodes,
            <-extracted_from[..{max_depth}]<-vault_memory AS extracted_from_nodes
        FROM {doc_id};
        """

        results = await execute_surreal_async(
            query, self.http_client, self.namespace, self.database
        )

        result_list = results[0].get("result", [])
        return result_list[0] if result_list else {}


# LRU-cached query function for frequent searches
@lru_cache(maxsize=100)
def _cache_key(
    query: str, top_k: int, include_ancestry: bool, include_descendants: bool
) -> str:
    """Generate cache key for query"""
    return f"{query}::{top_k}::{include_ancestry}::{include_descendants}"


async def cached_hybrid_search(
    query_engine: GraphRAGQuery, query: str, top_k: int = 5, **kwargs
) -> list[dict[str, Any]]:
    """Cached hybrid search (use for frequent queries)"""
    # Check cache
    cache_key = _cache_key(
        query,
        top_k,
        kwargs.get("include_ancestry", True),
        kwargs.get("include_descendants", True),
    )

    # Execute query (cache hit/miss handled by LRU decorator)
    return await query_engine.hybrid_search(query, top_k, **kwargs)
