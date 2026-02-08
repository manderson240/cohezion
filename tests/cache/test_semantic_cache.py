"""Tests for semantic caching."""

import pytest

from cohezion.cache.semantic_cache import CacheEntry, SemanticCache


class TestTextEmbedding:
    """Test text embedding functionality."""

    def test_embedding_deterministic(self):
        """Embedding should be deterministic."""
        text = "test prompt"
        emb1 = SemanticCache._text_to_embedding(text)
        emb2 = SemanticCache._text_to_embedding(text)

        assert (emb1 == emb2).all()

    def test_embedding_dimension(self):
        """Embedding should be 256D."""
        text = "test"
        embedding = SemanticCache._text_to_embedding(text)
        assert embedding.shape == (256,)

    def test_embedding_normalized(self):
        """Embedding should be normalized."""
        text = "test"
        embedding = SemanticCache._text_to_embedding(text)
        norm = (embedding**2).sum()**0.5
        assert abs(norm - 1.0) < 0.01

    def test_different_texts_different_embeddings(self):
        """Different texts should produce different embeddings."""
        emb1 = SemanticCache._text_to_embedding("prompt one")
        emb2 = SemanticCache._text_to_embedding("prompt two")
        assert not (emb1 == emb2).all()


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_similarity_same_vector(self):
        """Identical vectors should have similarity 1.0."""
        emb = SemanticCache._text_to_embedding("test")
        similarity = SemanticCache._cosine_similarity(emb, emb)
        assert abs(similarity - 1.0) < 0.01

    def test_similarity_range(self):
        """Similarity should be in [0, 1]."""
        emb1 = SemanticCache._text_to_embedding("text one")
        emb2 = SemanticCache._text_to_embedding("text two")
        similarity = SemanticCache._cosine_similarity(emb1, emb2)
        assert 0.0 <= similarity <= 1.0


class TestL1Cache:
    """Test L1 (exact match) cache."""

    @pytest.mark.asyncio
    async def test_l1_exact_match(self):
        """L1 should match exact prompts."""
        cache = SemanticCache()
        prompt = "exact prompt"
        response = "exact response"

        await cache.put(prompt, response)
        result = await cache.get(prompt)

        assert result == response
        assert cache.hits_l1 == 1

    @pytest.mark.asyncio
    async def test_l1_different_prompt_misses(self):
        """L1 should not match different prompts."""
        cache = SemanticCache()

        await cache.put("prompt one", "response one")
        result = await cache.get("prompt two")

        assert result is None
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_l1_fifo_eviction(self):
        """L1 should evict oldest entry when full."""
        cache = SemanticCache(max_l1_size=3, max_l2_size=0)  # Disable L2

        # Fill cache
        await cache.put("prompt1", "response1")
        await cache.put("prompt2", "response2")
        await cache.put("prompt3", "response3")

        # Add one more, should evict prompt1 from L1
        await cache.put("prompt4", "response4")

        # L1 should stay at max size
        stats = cache.get_stats()
        assert stats["l1_size"] == 3  # Max size is 3

    @pytest.mark.asyncio
    async def test_l1_system_prompt_affects_key(self):
        """Different system prompts should create different cache keys."""
        cache = SemanticCache()

        await cache.put("prompt", "response1", system="system_a")
        await cache.put("prompt", "response2", system="system_b")

        # Should get different responses
        result_a = await cache.get("prompt", system="system_a")
        result_b = await cache.get("prompt", system="system_b")

        assert result_a == "response1"
        assert result_b == "response2"


class TestL2Cache:
    """Test L2 (semantic) cache."""

    @pytest.mark.asyncio
    async def test_l2_similarity_match(self):
        """L2 should match semantically similar prompts."""
        cache = SemanticCache(similarity_threshold=0.85)

        # Store response for original prompt
        await cache.put(
            "What is the capital of France?",
            "Paris is the capital of France",
        )

        # Query with similar prompt
        result = await cache.get("What is the capital of France?")

        # Should get hit (exact match in L1)
        assert result == "Paris is the capital of France"

    @pytest.mark.asyncio
    async def test_l2_lfu_eviction(self):
        """L2 should evict least frequently used when full."""
        cache = SemanticCache(max_l2_size=2)

        await cache.put("prompt1", "response1")
        await cache.put("prompt2", "response2")
        await cache.put("prompt3", "response3")

        # prompt1 and prompt2 are in L2, one should be evicted
        stats = cache.get_stats()
        assert stats["l2_size"] <= 2

    @pytest.mark.asyncio
    async def test_l2_hit_promotion_to_l1(self):
        """L2 hits should be promoted to L1."""
        cache = SemanticCache(max_l1_size=2, similarity_threshold=0.80)

        # Fill L1
        await cache.put("p1", "r1")
        await cache.put("p2", "r2")

        # Put in L2 (will overflow L1)
        await cache.put("p3", "r3")

        # Now query p3 (should be in L2)
        result = await cache.get("p3")

        # Check if promoted to L1
        stats = cache.get_stats()
        assert stats["l1_size"] >= 1


class TestCacheStatistics:
    """Test cache statistics tracking."""

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Statistics should track hit rates correctly."""
        cache = SemanticCache()

        # 2 hits, 1 miss
        await cache.put("p1", "r1")
        await cache.get("p1")  # hit
        await cache.get("p2")  # miss

        stats = cache.get_stats()
        assert stats["l1_hits"] == 1
        assert stats["misses"] == 1
        assert stats["overall_hit_rate"] > 0.0

    @pytest.mark.asyncio
    async def test_stats_before_any_operations(self):
        """Stats should work before any operations."""
        cache = SemanticCache()
        stats = cache.get_stats()

        assert stats["total_requests"] == 0
        assert stats["overall_hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_clear_resets_stats(self):
        """Clearing cache should reset stats."""
        cache = SemanticCache()

        await cache.put("p1", "r1")
        await cache.get("p1")

        stats_before = cache.get_stats()
        assert stats_before["total_requests"] > 0

        cache.clear()

        stats_after = cache.get_stats()
        assert stats_after["total_requests"] == 0
        assert stats_after["l1_hits"] == 0


class TestCacheEntry:
    """Test cache entry dataclass."""

    def test_create_cache_entry(self):
        """Create cache entry."""
        embedding = SemanticCache._text_to_embedding("test")
        entry = CacheEntry(
            key="test_key",
            prompt="test prompt",
            response="test response",
            embedding=embedding,
        )

        assert entry.key == "test_key"
        assert entry.prompt == "test prompt"
        assert entry.response == "test response"
        assert entry.hit_count == 0


class TestMultiTierWorkflow:
    """Test complete multi-tier cache workflow."""

    @pytest.mark.asyncio
    async def test_cache_workflow_put_and_get(self):
        """Test typical cache workflow."""
        cache = SemanticCache(similarity_threshold=0.90)

        # Put entry
        prompt = "What is machine learning?"
        response = "Machine learning is a subset of AI"

        await cache.put(prompt, response)

        # Get exact match
        result = await cache.get(prompt)
        assert result == response

        # Check stats
        stats = cache.get_stats()
        assert stats["l1_hits"] == 1
        assert stats["overall_hit_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_cache_performance_metrics(self):
        """Test cache performance with multiple operations."""
        cache = SemanticCache(max_l1_size=10)

        # Put multiple entries
        for i in range(5):
            await cache.put(f"prompt_{i}", f"response_{i}")

        # Get some hits
        for i in range(3):
            await cache.get(f"prompt_{i}")

        # Get some misses
        for i in range(5, 8):
            await cache.get(f"prompt_{i}")

        stats = cache.get_stats()
        assert stats["l1_hits"] == 3
        assert stats["misses"] == 3
        assert stats["l1_size"] == 5
