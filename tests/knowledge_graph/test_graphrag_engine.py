"""Unit tests for GraphRAGEngine — vector + graph + temporal retrieval.

All tests use a mocked SurrealDB client (AsyncMock) so no live DB is needed.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from cohezion.knowledge_graph.graphrag_engine import (
    GraphRAGEngine,
    GraphRAGResponse,
    RetrievalResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EMBEDDING = [0.1] * 768  # 768-dim dummy embedding matching HNSW index

_SAMPLE_ROW = {
    "id": "neurons:abc123",
    "title": "Test Neuron",
    "content": "This is a test knowledge node.",
    "score": 0.92,
    "connections": [{"id": "neurons:xyz789", "title": "Related Node"}],
    "valid_from": datetime(2026, 1, 1),
    "valid_to": None,
}

_OK_RESPONSE = [{"status": "OK", "result": [_SAMPLE_ROW]}]


def _make_client(return_value=None) -> AsyncMock:
    """Return an AsyncMock client whose .query() returns *return_value*."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=return_value or _OK_RESPONSE)
    return client


# ---------------------------------------------------------------------------
# vector_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_calls_client() -> None:
    """vector_search passes embedding as a query param to the SurrealDB client."""
    client = _make_client()
    engine = GraphRAGEngine(surreal_client=client, default_top_k=3)

    await engine.vector_search(_EMBEDDING, top_k=3)

    client.query.assert_awaited_once()
    _, kwargs = client.query.call_args
    # params are passed as the second positional arg
    call_args = client.query.call_args[0]
    assert call_args[1]["query_embedding"] == _EMBEDDING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_parses_results() -> None:
    """vector_search correctly maps DB rows to RetrievalResult instances."""
    engine = GraphRAGEngine(surreal_client=_make_client(), default_top_k=5)

    response = await engine.vector_search(_EMBEDDING)

    assert isinstance(response, GraphRAGResponse)
    assert response.mode == "vector"
    assert len(response.results) == 1

    result = response.results[0]
    assert isinstance(result, RetrievalResult)
    assert result.neuron_id == "neurons:abc123"
    assert result.title == "Test Neuron"
    assert result.content == "This is a test knowledge node."
    assert result.score == pytest.approx(0.92)
    assert result.valid_from == datetime(2026, 1, 1)


# ---------------------------------------------------------------------------
# graph_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_search_uses_neuron_id() -> None:
    """graph_search forwards neuron_id as a query param."""
    client = _make_client()
    engine = GraphRAGEngine(surreal_client=client)

    await engine.graph_search("neurons:seed42")

    call_args = client.query.call_args[0]
    assert call_args[1]["neuron_id"] == "neurons:seed42"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_search_mode_is_graph() -> None:
    """graph_search response has mode == 'graph'."""
    engine = GraphRAGEngine(surreal_client=_make_client())
    response = await engine.graph_search("neurons:seed42")
    assert response.mode == "graph"


# ---------------------------------------------------------------------------
# temporal_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_temporal_search_includes_date_filter() -> None:
    """temporal_search embeds the ISO date string in the SurrealQL query."""
    client = _make_client()
    engine = GraphRAGEngine(surreal_client=client)
    as_of = datetime(2025, 6, 15, 12, 0, 0)

    await engine.temporal_search(_EMBEDDING, as_of=as_of)

    executed_query: str = client.query.call_args[0][0]
    assert "2025-06-15" in executed_query
    assert "valid_from" in executed_query
    assert "valid_to" in executed_query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_temporal_search_mode_is_temporal() -> None:
    """temporal_search response has mode == 'temporal'."""
    engine = GraphRAGEngine(surreal_client=_make_client())
    response = await engine.temporal_search(_EMBEDDING, as_of=datetime(2025, 6, 15))
    assert response.mode == "temporal"


# ---------------------------------------------------------------------------
# hybrid_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_includes_connections() -> None:
    """hybrid_search query selects ->synapses->neurons connections."""
    client = _make_client()
    engine = GraphRAGEngine(surreal_client=client)

    await engine.hybrid_search(_EMBEDDING)

    executed_query: str = client.query.call_args[0][0]
    assert "connections" in executed_query
    assert "synapses" in executed_query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_temporal_filter_when_as_of_provided() -> None:
    """hybrid_search injects temporal WHERE clause only when as_of is given."""
    client = _make_client()
    engine = GraphRAGEngine(surreal_client=client)
    as_of = datetime(2025, 3, 1)

    await engine.hybrid_search(_EMBEDDING, as_of=as_of)

    executed_query: str = client.query.call_args[0][0]
    assert "2025-03-01" in executed_query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_no_temporal_filter_without_as_of() -> None:
    """hybrid_search omits temporal WHERE clause when as_of is None."""
    client = _make_client()
    engine = GraphRAGEngine(surreal_client=client)

    await engine.hybrid_search(_EMBEDDING)

    executed_query: str = client.query.call_args[0][0]
    # temporal_filter string should be empty — no date literal in query
    assert "valid_from <=" not in executed_query


# ---------------------------------------------------------------------------
# No client / error cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_client_returns_empty() -> None:
    """When client is None every search method returns an empty GraphRAGResponse."""
    engine = GraphRAGEngine(surreal_client=None)

    for coro in [
        engine.vector_search(_EMBEDDING),
        engine.graph_search("neurons:x"),
        engine.temporal_search(_EMBEDDING, as_of=datetime(2025, 1, 1)),
        engine.hybrid_search(_EMBEDDING),
    ]:
        response = await coro
        assert isinstance(response, GraphRAGResponse)
        assert response.results == []
        assert response.total_results == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_error_returns_empty() -> None:
    """When the client raises, _execute_query returns empty (non-blocking)."""
    client = AsyncMock()
    client.query = AsyncMock(side_effect=RuntimeError("DB unreachable"))
    engine = GraphRAGEngine(surreal_client=client)

    response = await engine.vector_search(_EMBEDDING)

    assert isinstance(response, GraphRAGResponse)
    assert response.results == []
    assert response.total_results == 0


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_response_query_time_tracked() -> None:
    """query_time_ms is positive after a successful query."""
    engine = GraphRAGEngine(surreal_client=_make_client())
    response = await engine.vector_search(_EMBEDDING)
    assert response.query_time_ms > 0
