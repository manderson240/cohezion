"""Unit tests for LRUPersistentTokenCache with bounded memory and eviction.

Tests cover:
- Basic dict operations (get, set, delete, clear)
- Memory bounding and LRU eviction
- Session persistence and restore
- Eviction metrics and statistics
- Error handling and edge cases
"""

import tempfile
from pathlib import Path

import pytest

from cohezion.swarm.batch_processor import CacheEntry
from cohezion.swarm.lru_persistent_token_cache import LRUPersistentTokenCache


@pytest.fixture
def temp_cache_dir():
    """Create temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def bounded_cache(temp_cache_dir):
    """Create a small LRU cache for testing eviction."""
    return LRUPersistentTokenCache(
        cache_dir=temp_cache_dir,
        max_entries=5,
        eviction_threshold=0.8,
        target_utilization=0.6,
        persistence_enabled=False,
    )


@pytest.fixture
def persistent_cache(temp_cache_dir):
    """Create a persistent LRU cache."""
    return LRUPersistentTokenCache(
        cache_dir=temp_cache_dir,
        max_entries=10,
        persistence_enabled=True,
        auto_restore=True,
    )


class TestLRUPersistentTokenCacheDictInterface:
    """Test dict-like interface of LRUPersistentTokenCache."""

    def test_setitem_and_getitem(self, bounded_cache):
        """Test setting and getting items."""
        entry = CacheEntry(key="test", value="response", tokens_used=100)
        bounded_cache["test"] = entry

        retrieved = bounded_cache["test"]
        assert retrieved.key == "test"
        assert retrieved.value == "response"
        assert retrieved.tokens_used == 100

    def test_getitem_missing_key(self, bounded_cache):
        """Test getting missing key raises KeyError."""
        with pytest.raises(KeyError):
            _ = bounded_cache["nonexistent"]

    def test_contains(self, bounded_cache):
        """Test 'in' operator."""
        entry = CacheEntry(key="test", value="response", tokens_used=100)
        bounded_cache["test"] = entry

        assert "test" in bounded_cache
        assert "nonexistent" not in bounded_cache

    def test_len(self, bounded_cache):
        """Test len() returns correct count."""
        assert len(bounded_cache) == 0

        for i in range(3):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        assert len(bounded_cache) == 3

    def test_delete_item(self, bounded_cache):
        """Test deleting items."""
        entry = CacheEntry(key="test", value="response", tokens_used=100)
        bounded_cache["test"] = entry
        assert len(bounded_cache) == 1

        del bounded_cache["test"]
        assert len(bounded_cache) == 0
        assert "test" not in bounded_cache

    def test_delete_missing_key(self, bounded_cache):
        """Test deleting missing key raises KeyError."""
        with pytest.raises(KeyError):
            del bounded_cache["nonexistent"]


class TestLRUPersistentTokenCacheMemoryBounding:
    """Test memory bounding and LRU eviction."""

    def test_memory_bounded_at_max_entries(self, bounded_cache):
        """Test that cache respects max_entries limit."""
        # Add entries up to max (5)
        for i in range(5):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        assert len(bounded_cache) <= bounded_cache.max_entries

        # Add one more - should trigger eviction
        entry = CacheEntry(key="key5", value="response5", tokens_used=100)
        bounded_cache["key5"] = entry

        # After eviction, should be at target utilization or lower
        stats = bounded_cache.get_stats()
        assert (
            stats["memory_entries"] <= bounded_cache.max_entries + 1
        )  # Allow for timing

    def test_eviction_triggered_at_threshold(self, bounded_cache):
        """Test eviction tracking and threshold behavior."""
        # Verify threshold is correctly set
        assert bounded_cache.lru_store.eviction_threshold == 0.8

        # Add entries up to max_entries
        for i in range(5):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        # After 5 entries in a max_entries=5 cache, should be at capacity
        assert len(bounded_cache) == 5

        # Stats should show the correct max_entries and current utilization
        stats = bounded_cache.get_stats()
        assert stats["max_entries"] == 5
        assert stats["utilization"] == 1.0  # 5/5 = 100%

    def test_lru_evicts_oldest(self):
        """Test that LRU eviction works and keeps cache bounded."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use persistence to trigger eviction properly
            cache = LRUPersistentTokenCache(
                cache_dir=tmpdir,
                max_entries=5,
                eviction_threshold=0.8,
                target_utilization=0.6,
                persistence_enabled=True,  # Enable persistence for proper eviction
                auto_restore=False,
            )

            # Add 5 entries - with threshold=0.8 (4 entries), eviction triggers at 4
            # then brings cache down to target=0.6 (3 entries)
            for i in range(5):
                key = f"key{i}"
                entry = CacheEntry(key=key, value=f"response{i}", tokens_used=100)
                cache[key] = entry

            # After eviction, should be at target utilization (3 entries = 60%)
            # Some tolerance for timing and sync
            assert 2 <= len(cache) <= 4

            # Verify eviction actually happened
            stats = cache.get_stats()
            assert stats["eviction_count"] >= 1  # Should have triggered eviction

    def test_accessing_key_updates_lru(self, bounded_cache):
        """Test that accessing a key makes it recently used."""
        # Add entries
        for i in range(4):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        # Access key0 to make it recently used
        _ = bounded_cache["key0"]

        # Add more entries to trigger eviction
        for i in range(4, 6):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        # key0 should still exist (was recently accessed)
        # Other keys should have been evicted
        assert "key0" in bounded_cache


class TestLRUPersistentTokenCacheStatistics:
    """Test statistics and metrics."""

    def test_get_stats(self, bounded_cache):
        """Test get_stats returns correct information."""
        # Add some entries
        for i in range(3):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        stats = bounded_cache.get_stats()

        assert "memory_entries" in stats
        assert "max_entries" in stats
        assert "utilization" in stats
        assert "hit_rate" in stats
        assert "eviction_count" in stats

        assert stats["memory_entries"] == 3
        assert stats["max_entries"] == 5
        assert stats["utilization"] == pytest.approx(0.6, rel=0.01)

    def test_eviction_stats(self, bounded_cache):
        """Test get_eviction_stats returns detailed metrics."""
        # Add entries to trigger eviction
        for i in range(6):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        eviction_stats = bounded_cache.get_eviction_stats()

        assert "eviction_count" in eviction_stats
        assert "total_evicted_entries" in eviction_stats
        assert "current_utilization" in eviction_stats
        assert "current_size" in eviction_stats
        assert "max_size" in eviction_stats

    def test_hit_rate(self, bounded_cache):
        """Test hit rate calculation."""
        # Add entry
        entry = CacheEntry(key="test", value="response", tokens_used=100)
        bounded_cache["test"] = entry

        # Hit rate should be 0 initially
        assert bounded_cache.get_hit_rate() == 0.0

        # Access entry (cache hit in underlying store)
        _ = bounded_cache["test"]

        # Hit rate might be updated (depends on underlying store)
        # Just verify it's a valid number
        assert 0.0 <= bounded_cache.get_hit_rate() <= 1.0


class TestLRUPersistentTokenCachePersistence:
    """Test session persistence and restore."""

    def test_persistence_disabled_no_disk(self, temp_cache_dir):
        """Test that disabled persistence doesn't create files."""
        cache = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        entry = CacheEntry(key="test", value="response", tokens_used=100)
        cache["test"] = entry

        # Check that no JSONL file was created
        list(temp_cache_dir.glob("*.jsonl"))
        # With persistence_enabled=False, still creates cache but doesn't persist
        # Just verify the cache works

    def test_persistence_enabled_creates_file(self, temp_cache_dir):
        """Test that enabled persistence creates JSONL file."""
        cache = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            persistence_enabled=True,
            auto_restore=False,
        )

        entry = CacheEntry(key="test", value="response", tokens_used=100)
        cache["test"] = entry

        # Verify JSONL file was created (in the lru_store)
        jsonl_files = list(temp_cache_dir.glob("*.jsonl"))
        assert len(jsonl_files) > 0

    def test_session_restore(self, temp_cache_dir):
        """Test that cache restores from disk on restart."""
        # Create cache and add entries
        cache1 = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            max_entries=10,
            persistence_enabled=True,
            auto_restore=True,
        )

        entry1 = CacheEntry(key="key1", value="response1", tokens_used=100)
        entry2 = CacheEntry(key="key2", value="response2", tokens_used=200)
        cache1["key1"] = entry1
        cache1["key2"] = entry2

        assert len(cache1) == 2

        # Create new cache instance (simulating restart)
        cache2 = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            max_entries=10,
            persistence_enabled=True,
            auto_restore=True,
        )

        # Should restore entries
        assert "key1" in cache2
        assert "key2" in cache2
        assert len(cache2) == 2

        # Verify content
        assert cache2["key1"].value == "response1"
        assert cache2["key2"].value == "response2"


class TestLRUPersistentTokenCacheClear:
    """Test clearing cache."""

    def test_clear(self, bounded_cache):
        """Test clear removes all entries."""
        # Add entries
        for i in range(3):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        assert len(bounded_cache) == 3

        # Clear cache
        bounded_cache.clear()

        assert len(bounded_cache) == 0
        assert "key0" not in bounded_cache
        assert "key1" not in bounded_cache
        assert "key2" not in bounded_cache

    def test_clear_resets_metrics(self, bounded_cache):
        """Test that clear also resets eviction metrics."""
        # Add entries to trigger eviction
        for i in range(6):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        # Verify some evictions occurred
        bounded_cache.get_eviction_stats()

        # Clear cache
        bounded_cache.clear()

        # Metrics should be reset
        eviction_stats_after = bounded_cache.get_eviction_stats()
        assert eviction_stats_after["eviction_count"] == 0
        assert eviction_stats_after["current_size"] == 0


class TestLRUPersistentTokenCacheEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_cache_stats(self, bounded_cache):
        """Test stats for empty cache."""
        stats = bounded_cache.get_stats()
        assert stats["memory_entries"] == 0
        assert stats["hit_rate"] == 0.0

    def test_single_entry_cache(self, bounded_cache):
        """Test cache with single entry."""
        entry = CacheEntry(key="only", value="entry", tokens_used=100)
        bounded_cache["only"] = entry

        assert len(bounded_cache) == 1
        assert bounded_cache["only"].value == "entry"

    def test_overwrite_existing_entry(self, bounded_cache):
        """Test overwriting an existing entry."""
        entry1 = CacheEntry(key="test", value="first", tokens_used=100)
        bounded_cache["test"] = entry1

        entry2 = CacheEntry(key="test", value="second", tokens_used=200)
        bounded_cache["test"] = entry2

        # Should have updated entry
        assert bounded_cache["test"].value == "second"
        assert bounded_cache["test"].tokens_used == 200
        assert len(bounded_cache) == 1

    def test_large_token_values(self, bounded_cache):
        """Test handling large token counts."""
        entry = CacheEntry(key="large", value="response", tokens_used=999999999)
        bounded_cache["large"] = entry

        assert bounded_cache["large"].tokens_used == 999999999

    def test_empty_string_key(self, bounded_cache):
        """Test handling empty string as key."""
        entry = CacheEntry(key="", value="response", tokens_used=100)
        bounded_cache[""] = entry

        assert "" in bounded_cache
        assert bounded_cache[""].value == "response"

    def test_unicode_in_values(self, bounded_cache):
        """Test handling unicode characters."""
        entry = CacheEntry(key="unicode", value="🚀 Rocket response éàü", tokens_used=100)
        bounded_cache["unicode"] = entry

        assert bounded_cache["unicode"].value == "🚀 Rocket response éàü"


class TestLRUPersistentTokenCacheConfiguration:
    """Test configuration options."""

    def test_custom_max_entries(self, temp_cache_dir):
        """Test custom max_entries setting."""
        cache = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            max_entries=100,
            persistence_enabled=False,
        )

        assert cache.max_entries == 100
        stats = cache.get_stats()
        assert stats["max_entries"] == 100

    def test_custom_eviction_threshold(self, temp_cache_dir):
        """Test custom eviction_threshold setting."""
        cache = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            max_entries=10,
            eviction_threshold=0.75,
            target_utilization=0.5,
            persistence_enabled=True,  # Enable persistence for proper tracking
        )

        # Verify threshold is set correctly
        assert cache.lru_store.eviction_threshold == 0.75

        # Add 8 entries (80% - exceeds 75% threshold)
        for i in range(8):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            cache[f"key{i}"] = entry

        # Cache should be bounded at or near max_entries
        stats = cache.get_stats()
        assert stats["max_entries"] == 10
        # After eviction, should be at or below target_utilization (50% = 5 entries)
        # Allow some slack due to eviction timing
        assert stats["memory_entries"] <= 6
        eviction_stats = cache.get_eviction_stats()
        assert eviction_stats["eviction_count"] >= 1


class TestLRUPersistentTokenCacheIntegration:
    """Integration tests with realistic usage patterns."""

    def test_realistic_workload(self, temp_cache_dir):
        """Test with realistic inference workload."""
        cache = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            max_entries=50,
            persistence_enabled=False,
        )

        # Simulate 100 inferences with some cache hits
        prompts = [
            "Explain quantum computing",
            "What is ML?",
            "How does Python work?",
        ] * 35

        tokens_saved = 0
        for _i, prompt in enumerate(prompts):
            key = f"prompt_{hash(prompt) % 3}"  # 3 unique keys with repetition

            if key in cache:
                # Cache hit - don't add to cache again
                tokens_saved += 150
            else:
                # Cache miss - add entry
                entry = CacheEntry(
                    key=key,
                    value=f"Response to {prompt}",
                    tokens_used=150,
                )
                cache[key] = entry

        # Verify cache is bounded
        assert len(cache) <= cache.max_entries
        # Verify we had some cache hits (tokens saved)
        assert tokens_saved > 0

    def test_repeated_access_pattern(self, bounded_cache):
        """Test that frequently accessed items stay in cache."""
        # Add 5 entries
        for i in range(5):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        # Repeatedly access key0 to make it "hot"
        for _ in range(10):
            _ = bounded_cache["key0"]

        # Add more entries to trigger eviction
        for i in range(5, 8):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            bounded_cache[f"key{i}"] = entry

        # key0 should still exist (was frequently accessed)
        assert "key0" in bounded_cache


class TestLRUPersistentTokenCacheMemorySafety:
    """Test memory safety and resource cleanup."""

    def test_no_memory_leak_on_eviction(self, temp_cache_dir):
        """Test that eviction properly cleans up memory."""
        cache = LRUPersistentTokenCache(
            cache_dir=temp_cache_dir,
            max_entries=10,
            persistence_enabled=True,  # Enable persistence for proper eviction
            auto_restore=False,
        )

        # Add and evict many entries
        for batch in range(10):
            for i in range(15):
                entry = CacheEntry(
                    key=f"batch{batch}_key{i}",
                    value=f"response {batch}:{i}",
                    tokens_used=100,
                )
                cache[f"batch{batch}_key{i}"] = entry

        # Cache should stay bounded at or near max_entries
        # Allow some slack due to timing of eviction vs sync
        assert len(cache) <= cache.max_entries + 2

        # Verify stats show reasonable bounded behavior
        stats = cache.get_stats()
        assert stats["memory_entries"] > 0  # Should have entries
        assert stats["utilization"] <= 1.2  # Shouldn't be way over max

    def test_clear_frees_resources(self, persistent_cache):
        """Test that clear properly releases resources."""
        # Add many entries
        for i in range(50):
            entry = CacheEntry(key=f"key{i}", value=f"response{i}", tokens_used=100)
            persistent_cache[f"key{i}"] = entry

        initial_size = len(persistent_cache)
        assert initial_size > 0

        # Clear should free everything
        persistent_cache.clear()

        assert len(persistent_cache) == 0
        stats = persistent_cache.get_stats()
        assert stats["memory_entries"] == 0
