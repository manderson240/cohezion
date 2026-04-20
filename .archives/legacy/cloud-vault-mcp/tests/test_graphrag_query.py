"""Tests for GraphRAG hybrid query"""

import os

import pytest

from mcp_server.graphrag_query import GraphRAGQuery, _cache_key


_IN_CI = os.environ.get("CI") == "true"
_SKIP_REASON = "Requires Ollama/SurrealDB — unavailable in CI"


@pytest.mark.asyncio
@pytest.mark.skipif(_IN_CI, reason=_SKIP_REASON)
async def test_semantic_search():
    """Test semantic vector search"""
    async with GraphRAGQuery() as query:
        results = await query.semantic_search("test query", top_k=3)
        assert isinstance(results, list)
        # Should return results if vault has documents
        if results:
            assert "id" in results[0]
            assert "score" in results[0]


@pytest.mark.asyncio
@pytest.mark.skipif(_IN_CI, reason=_SKIP_REASON)
async def test_hybrid_search():
    """Test hybrid semantic + graph search"""
    async with GraphRAGQuery() as query:
        results = await query.hybrid_search("test query", top_k=3)
        assert isinstance(results, list)
        # Should have graph fields even if empty
        if results:
            doc = results[0]
            assert "id" in doc
            assert "score" in doc
            # ancestors/descendants may be None if no edges
            assert "ancestors" in doc or "descendants" in doc


@pytest.mark.asyncio
@pytest.mark.skipif(_IN_CI, reason=_SKIP_REASON)
async def test_find_related():
    """Test finding related documents via graph"""
    async with GraphRAGQuery() as query:
        # Use a document we know exists
        result = await query.find_related("vault_memory:template")
        assert isinstance(result, dict)
        # Should have relationship fields
        assert "id" in result or not result  # Empty if doc doesn't exist


def test_cache_key():
    """Test cache key generation"""
    key1 = _cache_key("query1", 5, True, False)
    key2 = _cache_key("query1", 5, True, False)
    key3 = _cache_key("query2", 5, True, False)

    assert key1 == key2  # Same params = same key
    assert key1 != key3  # Different query = different key


@pytest.mark.asyncio
@pytest.mark.skipif(_IN_CI, reason=_SKIP_REASON)
async def test_embedding_generation():
    """Test query embedding generation"""
    async with GraphRAGQuery() as query:
        embedding = await query.generate_embedding("test text")
        assert isinstance(embedding, list)
        assert len(embedding) == 768  # nomic-embed-text dimension


@pytest.mark.asyncio
@pytest.mark.skipif(_IN_CI, reason=_SKIP_REASON)
async def test_min_score_filter():
    """Test minimum score filtering"""
    async with GraphRAGQuery() as query:
        # High min_score should return fewer results
        results_high = await query.semantic_search("test", top_k=10, min_score=0.8)
        results_low = await query.semantic_search("test", top_k=10, min_score=0.1)

        assert len(results_high) <= len(results_low)
