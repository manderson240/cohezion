"""GraphRAG unified query engine — vector + graph + temporal in SurrealQL.

Combines three retrieval modes in single queries:
1. Vector: HNSW cosine similarity on neuron embeddings
2. Graph: Traverse synapses to find connected context
3. Temporal: VERSION clause for point-in-time queries

References:
    - Microsoft GraphRAG: Hierarchical community detection
    - Graphiti (Zep AI): Bi-temporal edge model (arXiv:2501.13956)
    - SurrealDB KG RAG patterns
    - Session 96b Phase 6
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieved item from GraphRAG query."""

    neuron_id: str
    title: str
    content: str
    score: float  # Similarity score
    connections: list[dict[str, Any]] = field(
        default_factory=list
    )  # Connected neurons via synapses
    valid_from: datetime | None = None
    valid_to: datetime | None = None


@dataclass
class GraphRAGResponse:
    """Aggregated response from a GraphRAG query."""

    results: list[RetrievalResult]
    query: str
    mode: str  # "vector", "graph", "hybrid", "temporal"
    total_results: int = 0
    query_time_ms: float = 0.0


class GraphRAGEngine:
    """Unified query engine combining vector + graph + temporal retrieval.

    All queries go through SurrealDB, leveraging:
    - HNSW index for vector similarity (cosine, 768-dim, EFC=150 M=12)
    - REFERENCE/tilde notation for graph traversal
    - Bi-temporal valid_from/valid_to filter for temporal point-in-time queries

    Parameters
    ----------
    surreal_client : Any | None
        Async SurrealDB client. When ``None`` every query returns an empty response.
    default_top_k : int
        Default number of results to return when ``top_k`` is not supplied.
    """

    def __init__(self, surreal_client: Any | None = None, default_top_k: int = 5) -> None:
        self._client = surreal_client
        self.default_top_k = default_top_k

    async def vector_search(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
    ) -> GraphRAGResponse:
        """Pure vector similarity search on neuron embeddings.

        Parameters
        ----------
        query_embedding : list[float]
            768-dim embedding vector matching the HNSW index dimension.
        top_k : int | None
            Number of results; defaults to ``self.default_top_k``.
        """
        k = top_k or self.default_top_k
        query = f"""
            SELECT id, title, content, embedding <|{k},40|> $query_embedding AS score
            FROM neurons
            WHERE embedding <|{k},40|> $query_embedding
            ORDER BY score DESC
            LIMIT {k};
        """
        return await self._execute_query(query, {"query_embedding": query_embedding}, "vector")

    async def graph_search(
        self,
        neuron_id: str,
        depth: int = 1,
    ) -> GraphRAGResponse:
        """Graph traversal from a seed neuron through synapses.

        Uses SurrealDB REFERENCE tilde notation to traverse ``synapses``
        edges in both directions (incoming and outgoing).

        Parameters
        ----------
        neuron_id : str
            Record ID of the seed neuron (e.g. ``"neurons:abc123"``).
        depth : int
            Traversal depth (currently 1-hop; future versions will support deeper).
        """
        query = """
            SELECT id, title, content,
                <-synapses<-neurons AS incoming,
                ->synapses->neurons AS outgoing
            FROM $neuron_id;
        """
        return await self._execute_query(query, {"neuron_id": neuron_id}, "graph")

    async def temporal_search(
        self,
        query_embedding: list[float],
        as_of: datetime,
        top_k: int | None = None,
    ) -> GraphRAGResponse:
        """Vector search at a specific point in time.

        Filters neurons whose valid-time window includes ``as_of``:
        ``valid_from <= as_of < valid_to`` (NULL valid_to = still active).

        Parameters
        ----------
        query_embedding : list[float]
            768-dim query embedding.
        as_of : datetime
            Point-in-time for the temporal filter.
        top_k : int | None
            Number of results; defaults to ``self.default_top_k``.
        """
        k = top_k or self.default_top_k
        iso = as_of.isoformat()
        query = f"""
            SELECT id, title, content, embedding <|{k},40|> $query_embedding AS score
            FROM neurons
            WHERE embedding <|{k},40|> $query_embedding
            AND valid_from <= d'{iso}'
            AND (valid_to IS NONE OR valid_to > d'{iso}')
            ORDER BY score DESC
            LIMIT {k};
        """
        return await self._execute_query(query, {"query_embedding": query_embedding}, "temporal")

    async def hybrid_search(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
        as_of: datetime | None = None,
    ) -> GraphRAGResponse:
        """Vector search + graph expansion + optional temporal filter.

        Pipeline:
        1. Find top-K neurons by embedding similarity (HNSW).
        2. Expand each via 1-hop synapse traversal (``->synapses->neurons``).
        3. Optionally filter by valid-time window when ``as_of`` is provided.

        Parameters
        ----------
        query_embedding : list[float]
            768-dim query embedding.
        top_k : int | None
            Number of seed neurons to retrieve; defaults to ``self.default_top_k``.
        as_of : datetime | None
            Optional point-in-time temporal filter.
        """
        k = top_k or self.default_top_k
        temporal_filter = ""
        if as_of:
            iso = as_of.isoformat()
            temporal_filter = (
                f"AND valid_from <= d'{iso}' AND (valid_to IS NONE OR valid_to > d'{iso}')"
            )

        query = f"""
            SELECT id, title, content,
                embedding <|{k},40|> $query_embedding AS score,
                ->synapses->neurons.{{id, title, valid_from}} AS connections
            FROM neurons
            WHERE embedding <|{k},40|> $query_embedding
            {temporal_filter}
            ORDER BY score DESC
            LIMIT {k};
        """
        return await self._execute_query(query, {"query_embedding": query_embedding}, "hybrid")

    async def _execute_query(
        self,
        query: str,
        params: dict[str, Any],
        mode: str,
    ) -> GraphRAGResponse:
        """Execute SurrealQL and parse into GraphRAGResponse.

        Returns an empty ``GraphRAGResponse`` (without raising) when the client
        is unavailable or the query fails — GraphRAG must never block the caller.
        """
        if self._client is None:
            logger.debug("No SurrealDB client available for GraphRAG query (mode=%s)", mode)
            return GraphRAGResponse(results=[], query=query, mode=mode)

        start = time.monotonic()
        try:
            raw = await self._client.query(query, params)
            elapsed_ms = (time.monotonic() - start) * 1000

            results: list[RetrievalResult] = []
            if raw and isinstance(raw, list) and raw[0].get("status") == "OK":
                for row in raw[0].get("result", []):
                    results.append(
                        RetrievalResult(
                            neuron_id=str(row.get("id", "")),
                            title=row.get("title", ""),
                            content=row.get("content", ""),
                            score=float(row.get("score", 0.0)),
                            connections=row.get("connections", []),
                            valid_from=row.get("valid_from"),
                            valid_to=row.get("valid_to"),
                        )
                    )

            return GraphRAGResponse(
                results=results,
                query=query,
                mode=mode,
                total_results=len(results),
                query_time_ms=elapsed_ms,
            )
        except Exception as e:
            logger.warning("GraphRAG query failed (mode=%s): %s", mode, e)
            return GraphRAGResponse(results=[], query=query, mode=mode)
