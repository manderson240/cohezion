"""Tests for vault search result caching."""

import time

import pytest

from mcp_server.search_cache import SearchCache
from mcp_server.vault_ops import VaultOps


class TestSearchCache:
    """Test SearchCache class."""

    def test_cache_hit(self):
        """Test that repeated accesses return cached value."""
        cache = SearchCache(ttl_seconds=60)
        value = [{"path": "test.md", "line": "test content"}]

        cache.set("query:all:", value)
        result1 = cache.get("query:all:")
        result2 = cache.get("query:all:")

        assert result1 == value
        assert result2 == value
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 0

    def test_cache_miss(self):
        """Test that missing keys return None."""
        cache = SearchCache(ttl_seconds=60)
        result = cache.get("nonexistent")
        assert result is None
        stats = cache.get_stats()
        assert stats["misses"] == 1

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = SearchCache(ttl_seconds=0.1)
        value = [{"path": "test.md"}]

        cache.set("query:all:", value)
        result1 = cache.get("query:all:")
        assert result1 == value

        # Wait for expiration
        time.sleep(0.2)
        result2 = cache.get("query:all:")
        assert result2 is None
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_cache_invalidate_specific(self):
        """Test invalidating specific cache entry."""
        cache = SearchCache(ttl_seconds=60)
        value1 = [{"path": "test1.md"}]
        value2 = [{"path": "test2.md"}]

        cache.set("query1:all:", value1)
        cache.set("query2:all:", value2)

        # Invalidate first key
        invalidated = cache.invalidate("query1:all:")
        assert invalidated is True

        # Verify first is gone, second remains
        assert cache.get("query1:all:") is None
        assert cache.get("query2:all:") == value2

        # Invalidating non-existent key returns False
        invalidated = cache.invalidate("nonexistent")
        assert invalidated is False

    def test_cache_invalidate_prefix(self):
        """Test invalidating by prefix."""
        cache = SearchCache(ttl_seconds=60)
        value1 = [{"path": "test1.md"}]
        value2 = [{"path": "test2.md"}]
        value3 = [{"path": "test3.md"}]

        cache.set("machine:all:", value1)
        cache.set("machine:folder:papers", value2)
        cache.set("learning:all:", value3)

        # Invalidate all "machine" prefixed keys
        count = cache.invalidate_prefix("machine")
        assert count == 2

        # Verify machine queries are gone, learning remains
        assert cache.get("machine:all:") is None
        assert cache.get("machine:folder:papers") is None
        assert cache.get("learning:all:") == value3

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = SearchCache(ttl_seconds=60)
        cache.set("query1:all:", [{"path": "test1.md"}])
        cache.set("query2:all:", [{"path": "test2.md"}])

        count = cache.clear()
        assert count == 2

        assert cache.get("query1:all:") is None
        assert cache.get("query2:all:") is None

    def test_cache_key_generation(self):
        """Test cache key generation is deterministic."""
        key1 = SearchCache.generate_key("test", "all", "")
        key2 = SearchCache.generate_key("test", "all", "")
        key3 = SearchCache.generate_key("test", "all", "folder")

        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 32  # MD5 hex length

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = SearchCache(ttl_seconds=60)
        value = [{"path": "test.md"}]

        # Initial stats
        stats = cache.get_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Add and hit
        cache.set("query:all:", value)
        cache.get("query:all:")
        cache.get("query:all:")

        # Miss
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(66.67, rel=1)

    def test_cache_reset_stats(self):
        """Test resetting cache statistics."""
        cache = SearchCache(ttl_seconds=60)
        value = [{"path": "test.md"}]

        cache.set("query:all:", value)
        cache.get("query:all:")
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["hits"] > 0
        assert stats["misses"] > 0

        cache.reset_stats()
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestVaultOpsWithCache:
    """Test VaultOps integration with SearchCache."""

    @pytest.fixture
    def vault_with_cache(self, tmp_path):
        """Create a vault with cache enabled."""
        (tmp_path / "papers").mkdir()
        (tmp_path / "papers" / "test1.md").write_text(
            "# Machine Learning Basics\n\n"
            "This paper discusses machine learning concepts.\n"
        )
        (tmp_path / "papers" / "test2.md").write_text(
            "# Deep Learning\n\nDeep learning is a subset of machine learning.\n"
        )
        (tmp_path / "papers" / "test3.md").write_text(
            "# Natural Language Processing\n\nNLP uses neural networks.\n"
        )
        return VaultOps(str(tmp_path), cache_enabled=True, cache_ttl_seconds=60)

    @pytest.fixture
    def vault_without_cache(self, tmp_path):
        """Create a vault with cache disabled."""
        (tmp_path / "papers").mkdir()
        (tmp_path / "papers" / "test1.md").write_text("# Test Paper\n\nContent here.\n")
        return VaultOps(str(tmp_path), cache_enabled=False)

    def test_vault_cache_hit_repeated_search(self, vault_with_cache):
        """Test that repeated searches return cached results."""
        # First search - populates cache
        results1 = vault_with_cache.search("machine")

        # Verify cache stats before second search
        stats = vault_with_cache.get_search_cache_stats()
        assert stats["enabled"] is True
        assert stats["hits"] == 0  # First search is not a hit

        # Second search - should be cache hit
        results2 = vault_with_cache.search("machine")

        # Results should be identical
        assert results1 == results2
        assert len(results1) > 0

        # Verify cache hit
        stats = vault_with_cache.get_search_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1  # Only the first search was a miss

    def test_vault_cache_different_queries(self, vault_with_cache):
        """Test that different queries use different cache entries."""
        results1 = vault_with_cache.search("machine")
        results2 = vault_with_cache.search("learning")

        # Results should be different
        assert results1 != results2

        # Both queries should be cached
        stats = vault_with_cache.get_search_cache_stats()
        assert stats["size"] == 2

    def test_vault_cache_different_scopes(self, vault_with_cache):
        """Test that different scopes use different cache entries."""
        results1 = vault_with_cache.search("test", scope="all")
        results2 = vault_with_cache.search("test", scope="tags")

        # Both should be cached separately
        stats = vault_with_cache.get_search_cache_stats()
        assert stats["size"] == 2

    def test_vault_cache_invalidation(self, vault_with_cache):
        """Test cache invalidation."""
        # Populate cache
        vault_with_cache.search("machine")
        stats = vault_with_cache.get_search_cache_stats()
        assert stats["size"] == 1

        # Invalidate all cache
        vault_with_cache.invalidate_search_cache()
        stats = vault_with_cache.get_search_cache_stats()
        assert stats["size"] == 0

    def test_vault_cache_invalidate_file(self, vault_with_cache):
        """Test cache invalidation on file change."""
        # Populate cache
        vault_with_cache.search("machine")
        assert vault_with_cache.get_search_cache_stats()["size"] == 1

        # Invalidate cache for a file change
        vault_with_cache.invalidate_search_cache_for_file("papers/test1.md")
        assert vault_with_cache.get_search_cache_stats()["size"] == 0

    def test_vault_cache_disabled(self, vault_without_cache):
        """Test that caching can be disabled."""
        # Run search
        vault_without_cache.search("test")

        # Stats should show cache disabled
        stats = vault_without_cache.get_search_cache_stats()
        assert stats["enabled"] is False

        # Invalidation should return 0
        count = vault_without_cache.invalidate_search_cache()
        assert count == 0

    def test_vault_cache_no_regression(self, vault_with_cache):
        """Test that cached results are identical to uncached searches."""
        results_cache = vault_with_cache.search("learning")

        # Create new vault instance without cache and search
        vault_ops = VaultOps(str(vault_with_cache.vault_path), cache_enabled=False)
        results_no_cache = vault_ops.search("learning")

        # Results should be identical
        assert results_cache == results_no_cache
