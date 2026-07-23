"""Discriminating tests for BM25 + RRF vault-retrieval fusion (Contextual-Retrieval, ~-49% failures).

Each test fails for a semantic-only impl (no lexical fusion / no promotion of buried exact matches).
"""

import asyncio

from mcp_server.graphrag_query import GraphRAGQuery, _bm25_scores, _rrf_fuse


DOCS = [
    "the compound loop orchestrates local agents efficiently",  # semantic-ish, no exact term
    "semantic cache dedup by cosine similarity threshold",  # unrelated
    "CB14 citation gate rejects uncited LM claims",  # EXACT term match
]


def test_bm25_favors_exact_term_match():
    s = _bm25_scores("CB14 citation gate", DOCS)
    # a no-op (all-zero / ignores terms) impl fails: the exact-term doc must score strictly highest
    assert s[2] > s[0] and s[2] > s[1], s


def test_rrf_promotes_a_lexically_top_but_semantically_buried_doc():
    # doc 2 is LAST in semantic order but FIRST in bm25 order → must rise out of last place
    fused = _rrf_fuse([[0, 1, 2], [2, 0, 1]])
    assert fused.index(2) < 2, fused
    # discriminating control: semantic-only fusion leaves it last
    assert _rrf_fuse([[0, 1, 2]]).index(2) == 2


def test_fused_search_promotes_buried_exact_match_into_top_k():
    q = GraphRAGQuery.__new__(
        GraphRAGQuery
    )  # bypass __init__; method only needs semantic_search

    async def fake_semantic(query, top_k=5, min_score=0.3):
        # cosine-desc pool; the exact-term doc (id 3) is ranked LAST semantically
        return [
            {"id": "1", "content": DOCS[0]},
            {"id": "2", "content": DOCS[1]},
            {"id": "3", "content": DOCS[2]},
        ]

    q.semantic_search = fake_semantic
    out = asyncio.run(q.bm25_fused_search("CB14 citation gate", top_k=2, pool=20))
    ids = [r["id"] for r in out]
    # semantic-only top-2 would be ["1","2"] and DROP the exact-term match; fusion must keep it
    assert "3" in ids, ids


def test_fused_search_degenerate_pool_is_safe():
    q = GraphRAGQuery.__new__(GraphRAGQuery)

    async def one_result(query, top_k=5, min_score=0.3):
        return [{"id": "1", "content": "solo"}]

    q.semantic_search = one_result
    assert asyncio.run(q.bm25_fused_search("x", top_k=5)) == [
        {"id": "1", "content": "solo"}
    ]
