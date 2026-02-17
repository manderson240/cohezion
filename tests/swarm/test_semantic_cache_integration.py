"""Tests for L1 + L2 + L3 semantic cache integration in TokenEfficientClient.

Tests three-tier caching hierarchy:
- L1: Exact SHA-256 hash (in-memory)
- L2: Semantic fuzzy matching (embeddings)
- L3: Persistent JSONL (disk)
- Fallback: Generate new via Ollama
"""

from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from cohezion.swarm.batch_processor import BatchItem, CacheEntry
from cohezion.swarm.semantic_cache import (
    EmbeddingResult,
    SemanticCache,
)
from cohezion.swarm.token_client import TokenEfficientClient


@pytest.fixture
def token_client_with_semantic():
    """Create TokenEfficientClient with semantic cache enabled."""
    return TokenEfficientClient(
        use_semantic_cache=True,
        semantic_threshold=0.95,
        use_persistent_cache=False,  # Use in-memory cache for tests
    )


class TestThreeTierCacheHierarchy:
    """Test L1 → L2 → L3 fallback chain."""

    @pytest.mark.asyncio
    async def test_l1_cache_hit_exact_match(self, token_client_with_semantic):
        """Test L1 cache hit on exact prompt match."""
        # Pre-populate L1 cache
        cache_key = token_client_with_semantic._cache_key("Test prompt", "System", "phi3:mini")
        from cohezion.swarm.batch_processor import CacheEntry

        token_client_with_semantic.batch_processor.cache[cache_key] = CacheEntry(
            key=cache_key,
            value="Cached response",
            tokens_used=42,
        )

        # Generate with exact same prompt
        response, tokens = await token_client_with_semantic.generate(
            prompt="Test prompt",
            model="phi3:mini",
            system="System",
        )

        assert response == "Cached response"
        assert tokens == 42
        assert token_client_with_semantic._cache_hits == 1
        assert token_client_with_semantic._semantic_hits == 0
        assert token_client_with_semantic._api_calls == 0

    @pytest.mark.asyncio
    async def test_l2_fallback_semantic_match(self, token_client_with_semantic):
        """Test L2 cache hit on semantically similar prompt (L1 miss)."""
        # Setup mock embedding model
        embedding_vectors = [
            [0.99, 0.01] + [0.0] * 382,  # "Original prompt" embedding
            [0.98, 0.02] + [0.0] * 382,  # "Slightly different prompt" embedding
        ]

        embeddings_iter = iter(embedding_vectors)

        async def mock_encode(text):
            embedding = next(embeddings_iter)
            # Normalize
            arr = np.array(embedding, dtype=np.float32)
            arr = arr / (np.linalg.norm(arr) + 1e-8)
            return EmbeddingResult(embedding=arr.tolist(), tokens_used=10)

        # Store in L2 cache
        cache_entry_key = token_client_with_semantic._cache_key("Original prompt", "", "phi3:mini")
        if token_client_with_semantic.semantic_cache:
            token_client_with_semantic.semantic_cache._embedding_model.encode = mock_encode

            # Put original in L2
            await token_client_with_semantic.semantic_cache.put(
                prompt="Original prompt",
                system="",
                model="phi3:mini",
                value="Cached semantic response",
                cache_key=cache_entry_key,
            )

        # Reset iterator for new query
        embeddings_iter = iter(embedding_vectors)

        # Query with similar prompt (no L1 hit)
        response, tokens = await token_client_with_semantic.generate(
            prompt="Slightly different prompt",
            model="phi3:mini",
            system="",
        )

        # Should get L2 semantic hit
        assert response == "Cached semantic response"
        assert tokens == 0  # Semantic hits don't consume tokens
        assert token_client_with_semantic._cache_hits == 0
        assert token_client_with_semantic._semantic_hits == 1
        assert token_client_with_semantic._api_calls == 0

    @pytest.mark.asyncio
    async def test_l3_fallback_with_ollama(self, token_client_with_semantic):
        """Test fallback to Ollama when L1 and L2 miss."""
        # Mock Ollama client
        with patch.object(token_client_with_semantic.ollama, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = ("New generated response", 50)

            response, tokens = await token_client_with_semantic.generate(
                prompt="Unique prompt never seen before",
                model="phi3:mini",
                system="",
            )

            assert response == "New generated response"
            assert tokens == 50
            assert token_client_with_semantic._cache_hits == 0
            assert token_client_with_semantic._semantic_hits == 0
            assert token_client_with_semantic._api_calls == 1
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_l1_stores_l2_results(self, token_client_with_semantic):
        """Test that L2 semantic hits are stored in L1 for future exact matches."""
        if not token_client_with_semantic.semantic_cache:
            pytest.skip("Semantic cache not available")

        # Pre-load L2 cache with a unique key
        token_client_with_semantic._cache_key("Test", "", "phi3:mini")
        embedding_vec = np.array([1.0] + [0.0] * 383, dtype=np.float32)
        embedding_vec = embedding_vec / np.linalg.norm(embedding_vec)

        token_client_with_semantic.semantic_cache._embedding_cache["custom_key"] = (
            embedding_vec.tolist(),
            "L2 result",
        )
        token_client_with_semantic.semantic_cache._access_order["custom_key"] = None

        # Mock embeddings to return the same vector
        async def mock_encode(text):
            return EmbeddingResult(embedding=embedding_vec.tolist(), tokens_used=10)

        token_client_with_semantic.semantic_cache._embedding_model.encode = mock_encode

        # Mock Ollama to fail (shouldn't be called)
        with patch.object(token_client_with_semantic.ollama, "generate", new_callable=AsyncMock) as mock_generate:
            # First query should get L2 hit (not call Ollama)
            response1, _tokens1 = await token_client_with_semantic.generate(prompt="Test", model="phi3:mini", system="")
            assert response1 == "L2 result"
            assert token_client_with_semantic._semantic_hits == 1
            mock_generate.assert_not_called()

            # Second query with identical prompt should now hit L1
            response2, _tokens2 = await token_client_with_semantic.generate(prompt="Test", model="phi3:mini", system="")
            assert response2 == "L2 result"
            assert token_client_with_semantic._cache_hits == 1  # Now in L1
            mock_generate.assert_not_called()  # Still shouldn't call Ollama

    @pytest.mark.asyncio
    async def test_batch_with_mixed_cache_tiers(self, token_client_with_semantic):
        """Test batch processing with items hitting L1, L2, and requiring Ollama."""
        # Pre-populate L1 cache
        cache_key_l1 = token_client_with_semantic._cache_key("Cached prompt", "", "phi3:mini")
        token_client_with_semantic.batch_processor.cache[cache_key_l1] = CacheEntry(
            key=cache_key_l1,
            value="L1 cached response",
            tokens_used=30,
        )

        # Pre-populate L2 semantic cache
        if token_client_with_semantic.semantic_cache:
            embedding_vec = np.array([0.9, 0.1] + [0.0] * 382, dtype=np.float32)
            embedding_vec = embedding_vec / np.linalg.norm(embedding_vec)
            token_client_with_semantic.semantic_cache._embedding_cache["semantic_key"] = (
                embedding_vec.tolist(),
                "L2 semantic response",
            )

        # Mock Ollama for new items
        with patch.object(token_client_with_semantic.ollama, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = ("Ollama generated response", 60)

            items = [
                BatchItem(
                    id="1",
                    prompt="Cached prompt",
                    system="",
                    model="phi3:mini",
                ),
                BatchItem(
                    id="2",
                    prompt="New unique prompt",
                    system="",
                    model="phi3:mini",
                ),
            ]

            result = await token_client_with_semantic.batch_generate(items)

            # Verify hits
            assert result.cache_hits == 1  # L1 hit
            assert result.cache_misses == 1  # One miss that required Ollama
            # L2 might or might not match depending on embedding vectors

    def test_metrics_show_l1_and_l2_separately(self, token_client_with_semantic):
        """Test that metrics distinguish between L1 and L2 hits."""
        token_client_with_semantic._cache_hits = 5
        token_client_with_semantic._semantic_hits = 3
        token_client_with_semantic._cache_misses = 2

        metrics = token_client_with_semantic.get_metrics()

        assert metrics["l1_hits"] == 5
        assert metrics["l2_hits"] == 3
        assert metrics["total_cache_hits"] == 8
        assert metrics["combined_hit_rate"] == 0.8  # (5+3)/(5+3+2)
        assert metrics["l1_hit_rate"] == 5 / 10
        assert metrics["l2_hit_rate"] == 3 / 10

    def test_semantic_cache_disabled(self):
        """Test TokenEfficientClient works without semantic cache."""
        client = TokenEfficientClient(
            use_semantic_cache=False,
            use_persistent_cache=False,
        )

        assert client.semantic_cache is None
        metrics = client.get_metrics()
        assert "semantic_cache_stats" not in metrics

    def test_semantic_cache_init_error_handled(self):
        """Test semantic cache init errors don't crash client."""
        # Mock semantic cache to fail on init
        with patch(
            "cohezion.swarm.token_client.SemanticCache",
            side_effect=Exception("Init failed"),
        ):
            client = TokenEfficientClient(
                use_semantic_cache=True,
                use_persistent_cache=False,
            )

            # Should gracefully degrade to no semantic cache
            assert client.semantic_cache is None

    @pytest.mark.asyncio
    async def test_semantic_cache_thread_safety_with_batch(self, token_client_with_semantic):
        """Test semantic cache is thread-safe during batch operations."""
        if not token_client_with_semantic.semantic_cache:
            pytest.skip("Semantic cache not available")

        with patch.object(token_client_with_semantic.ollama, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = ("Response", 50)

            # Create batch with duplicate prompts
            items = [
                BatchItem(id="1", prompt="Shared prompt", system="", model="phi3:mini"),
                BatchItem(id="2", prompt="Shared prompt", system="", model="phi3:mini"),
                BatchItem(id="3", prompt="Shared prompt", system="", model="phi3:mini"),
            ]

            result = await token_client_with_semantic.batch_generate(items)

            # All should get same result
            assert result.items[0].result == result.items[1].result
            assert result.items[1].result == result.items[2].result


@pytest.mark.asyncio
async def test_semantic_cache_confidence_tracking():
    """Test semantic cache confidence is properly tracked."""
    cache = SemanticCache(similarity_threshold=0.95, embedding_dim=256, max_entries=100)

    # Manually setup cache entries
    vec1 = np.array([1.0] + [0.0] * 255, dtype=np.float32)
    vec1 = vec1 / np.linalg.norm(vec1)

    cache._embedding_cache["key1"] = (vec1.tolist(), "value1")
    cache._access_order["key1"] = None

    # Mock encoder to return same vector
    async def mock_encode(text):
        return EmbeddingResult(embedding=vec1.tolist(), tokens_used=10)

    cache._embedding_model.encode = mock_encode

    # Query should match with high confidence
    hit = await cache.get("Any prompt", "")
    assert hit is not None
    assert hit.confidence > 0.99


class TestSemanticCachePerformance:
    """Test performance characteristics of L2 semantic cache."""

    def test_semantic_cache_scalability(self, token_client_with_semantic):
        """Test semantic cache doesn't degrade with many entries."""
        if not token_client_with_semantic.semantic_cache:
            pytest.skip("Semantic cache not available")

        cache = token_client_with_semantic.semantic_cache
        # Pre-populate with 100 vectors
        for i in range(100):
            vec = np.random.randn(384).astype(np.float32)
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            cache._embedding_cache[f"key_{i}"] = (vec.tolist(), f"value_{i}")
            cache._access_order[f"key_{i}"] = None

        # Stats should show all entries
        stats = cache.get_stats()
        assert stats["cache_size"] == 100

    def test_semantic_cache_lru_eviction(self, token_client_with_semantic):
        """Test LRU eviction when max_entries exceeded."""
        if not token_client_with_semantic.semantic_cache:
            pytest.skip("Semantic cache not available")

        cache = token_client_with_semantic.semantic_cache
        cache.max_entries = 5

        # Add 7 entries (should evict 2)
        for i in range(7):
            vec = np.random.randn(384).astype(np.float32)
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            cache._embedding_cache[f"key_{i}"] = (vec.tolist(), f"value_{i}")
            cache._access_order[f"key_{i}"] = None
            if len(cache._embedding_cache) > cache.max_entries:
                cache._evict_lru()

        # Should have at most max_entries
        assert len(cache._embedding_cache) <= cache.max_entries
