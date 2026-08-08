"""Wiring tests for GraphRAGEngine.lexical_hybrid_search.

These are CONSUMPTION invariants, not declaration invariants: each asserts that
the engine *reads the lexical index and acts on it*. The load-bearing test is
``test_rescues_document_the_vector_search_never_returned`` -- it fails against an
engine that accepts a ``lexical_index`` and then ignores it, which is precisely
the dormant-capability failure this repo keeps shipping.

Mutation-verified 2026-08-08: 6/6 mutants killed (index ignored, rerank-only,
mode always claiming hybrid, hollow results, lexical ranking dropped from RRF,
candidate depth collapsed to top_k).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cohezion.knowledge_graph.graphrag_engine import GraphRAGEngine
from cohezion.knowledge_graph.lexical_index import BM25Index


_EMBEDDING = [0.1] * 768

# The vector side returns four topically-similar documents and never returns
# the runbook, which is the only document containing the literal token.
_DENSE_ROWS = [
    {"id": "neurons:vec1", "title": "Vector search", "content": "cosine similarity", "score": 0.9},
    {"id": "neurons:vec2", "title": "HNSW", "content": "nearest neighbour index", "score": 0.8},
    {"id": "neurons:vec3", "title": "Reranking", "content": "cross encoder rerank", "score": 0.7},
    {"id": "neurons:vec4", "title": "Chunking", "content": "split documents", "score": 0.6},
]

_OPS_ROW = {
    "id": "neurons:ops1",
    "title": "Nightly batch runbook",
    "content": "on failure the process emits error code E2140 and the operator drains the queue",
    "score": 0.0,
}


def _index() -> BM25Index:
    idx = BM25Index()
    for row in [*_DENSE_ROWS, _OPS_ROW]:
        idx.add(row["id"], f"{row['title']} {row['content']}")
    return idx


def _client(dense_rows: list[dict], fetch_rows: list[dict] | None = None) -> AsyncMock:
    """Client that answers the vector query first, then the fetch-by-ids query."""
    responses = [
        [{"status": "OK", "result": dense_rows}],
        [{"status": "OK", "result": fetch_rows or []}],
    ]
    client = AsyncMock()
    client.query = AsyncMock(side_effect=responses + [[{"status": "OK", "result": []}]] * 5)
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_degrades_to_vector_when_no_index_configured() -> None:
    """No lexical index must report mode 'vector' -- never claim hybrid."""
    engine = GraphRAGEngine(surreal_client=_client(_DENSE_ROWS), default_top_k=3)
    resp = await engine.lexical_hybrid_search("anything", _EMBEDDING)
    assert resp.mode == "vector"
    assert len(resp.results) == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_index_also_degrades() -> None:
    """An index that exists but holds nothing is not a hybrid either."""
    engine = GraphRAGEngine(
        surreal_client=_client(_DENSE_ROWS), default_top_k=3, lexical_index=BM25Index()
    )
    resp = await engine.lexical_hybrid_search("anything", _EMBEDDING)
    assert resp.mode == "vector"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mode_reports_lexical_hybrid_when_fusion_runs() -> None:
    engine = GraphRAGEngine(
        surreal_client=_client(_DENSE_ROWS, [_OPS_ROW]),
        default_top_k=3,
        lexical_index=_index(),
    )
    resp = await engine.lexical_hybrid_search("E2140", _EMBEDDING)
    assert resp.mode == "lexical_hybrid"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rescues_document_the_vector_search_never_returned() -> None:
    """The whole point: a lexical-only hit must be fetched and surfaced.

    The dense side never returns neurons:ops1. An engine that ignores the
    lexical index, or that merely reranks the dense candidates, cannot produce
    it -- so this fails for both of those wrong implementations.
    """
    engine = GraphRAGEngine(
        surreal_client=_client(_DENSE_ROWS, [_OPS_ROW]),
        default_top_k=3,
        lexical_index=_index(),
    )
    resp = await engine.lexical_hybrid_search("E2140", _EMBEDDING)

    ids = [r.neuron_id for r in resp.results]
    assert "neurons:ops1" in ids, "lexical-only match was not rescued"
    assert ids[0] == "neurons:ops1", "exact-token match should rank first"
    # And it must carry real content, not a hollow placeholder.
    assert "E2140" in resp.results[0].content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_only_baseline_FAILS_the_same_query() -> None:
    """Discriminator: proves the rescue test measures the mechanism.

    Same corpus, same query, no lexical index -> the document is unreachable.
    If this ever starts finding ops1, the fixture stopped exercising hybrid
    retrieval and the test above would pass vacuously.
    """
    engine = GraphRAGEngine(surreal_client=_client(_DENSE_ROWS), default_top_k=3)
    resp = await engine.lexical_hybrid_search("E2140", _EMBEDDING)
    assert "neurons:ops1" not in [r.neuron_id for r in resp.results]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_semantic_query_still_returns_dense_results() -> None:
    """A query with no lexical signal must not be degraded by fusion."""
    engine = GraphRAGEngine(
        surreal_client=_client(_DENSE_ROWS, []),
        default_top_k=4,
        lexical_index=_index(),
    )
    resp = await engine.lexical_hybrid_search("zzzznomatch", _EMBEDDING)
    assert [r.neuron_id for r in resp.results] == [r["id"] for r in _DENSE_ROWS]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unretrievable_fused_id_is_skipped_not_hollow() -> None:
    """If the store cannot return a lexical-only hit, drop it.

    Emitting a RetrievalResult with an empty title/content would look like a
    real answer to a caller and is worse than returning fewer results.
    """
    engine = GraphRAGEngine(
        surreal_client=_client(_DENSE_ROWS, []),  # fetch-by-ids returns nothing
        default_top_k=5,
        lexical_index=_index(),
    )
    resp = await engine.lexical_hybrid_search("E2140", _EMBEDDING)
    assert all(r.content for r in resp.results)
    assert "neurons:ops1" not in [r.neuron_id for r in resp.results]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieves_deeper_than_top_k_for_rescue_depth() -> None:
    """Fusion must see more candidates than it returns.

    Asserted against the emitted SurrealQL rather than the returned rows: the
    AsyncMock replies with a fixed row list whatever depth is requested, so
    checking results alone cannot detect a collapsed candidate_k.
    """
    client = _client(_DENSE_ROWS, [_OPS_ROW])
    engine = GraphRAGEngine(surreal_client=client, default_top_k=3, lexical_index=_index())
    await engine.lexical_hybrid_search("E2140", _EMBEDDING, top_k=3, candidate_k=20)

    vector_query = client.query.await_args_list[0].args[0]
    assert "LIMIT 20" in vector_query, "vector side must be queried at candidate depth"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_client_returns_empty_without_raising() -> None:
    """GraphRAG must never block the caller, even fully unconfigured."""
    engine = GraphRAGEngine(surreal_client=None, lexical_index=_index())
    resp = await engine.lexical_hybrid_search("E2140", _EMBEDDING)
    assert resp.results == []
