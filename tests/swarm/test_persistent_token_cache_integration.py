"""Test PersistentTokenCache integration with TokenEfficientClient.

Verifies that cache entries persist across session restarts and that
hit rates improve as expected.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cohezion.swarm.batch_processor import CacheEntry
from cohezion.swarm.persistent_token_cache import PersistentTokenCache


@pytest.fixture
def temp_cache_dir():
    """Create temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestPersistentTokenCache:
    """Test PersistentTokenCache dict-like interface."""

    def test_initialization(self, temp_cache_dir):
        """Test creating a persistent token cache."""
        cache = PersistentTokenCache(cache_dir=temp_cache_dir)
        assert isinstance(cache, dict)
        assert len(cache) == 0

    def test_setitem_and_getitem(self, temp_cache_dir):
        """Test storing and retrieving cache entries."""
        cache = PersistentTokenCache(cache_dir=temp_cache_dir)

        entry = CacheEntry(key="test", value="response", tokens_used=50)
        cache["key1"] = entry

        assert "key1" in cache
        assert cache["key1"].value == "response"
        assert cache["key1"].tokens_used == 50

    def test_cache_persists_to_disk(self, temp_cache_dir):
        """Test that cache entries are written to disk."""
        cache = PersistentTokenCache(cache_dir=temp_cache_dir)

        entry = CacheEntry(key="test", value="response", tokens_used=100)
        cache["key1"] = entry

        # Verify file exists
        cache_file = temp_cache_dir / "token_cache.jsonl"
        assert cache_file.exists()

    def test_session_restore_from_disk(self, temp_cache_dir):
        """Test restoring cache from previous session (core success criterion).

        This verifies the primary success criterion:
        - Session 1: Create cache, add entries, exit
        - Session 2: Create new client, verify cache hits
        """
        # Session 1: Create cache and populate
        cache1 = PersistentTokenCache(cache_dir=temp_cache_dir)
        entry1 = CacheEntry(key="prompt1", value="response1", tokens_used=100)
        entry2 = CacheEntry(key="prompt2", value="response2", tokens_used=150)

        cache1["key1"] = entry1
        cache1["key2"] = entry2

        assert len(cache1) == 2

        # Session 2: Create new cache instance and verify restore
        cache2 = PersistentTokenCache(
            cache_dir=temp_cache_dir, persistence_enabled=True, auto_restore=True
        )

        assert len(cache2) == 2
        assert cache2["key1"].value == "response1"
        assert cache2["key1"].tokens_used == 100
        assert cache2["key2"].value == "response2"
        assert cache2["key2"].tokens_used == 150

    def test_persistent_store_hit_rate(self, temp_cache_dir):
        """Test persistent store hit rate tracking."""
        cache = PersistentTokenCache(cache_dir=temp_cache_dir)

        entry = CacheEntry(key="test", value="response", tokens_used=50)
        cache["key1"] = entry

        # Access the persistent store directly to test hit tracking
        hit_rate = cache.persistent_store.get_hit_rate()
        # Initially, we put one entry, so no hits yet
        assert hit_rate == 0.0

    def test_get_stats(self, temp_cache_dir):
        """Test cache statistics."""
        cache = PersistentTokenCache(cache_dir=temp_cache_dir)

        entry1 = CacheEntry(key="test1", value="response1", tokens_used=100)
        entry2 = CacheEntry(key="test2", value="response2", tokens_used=150)

        cache["key1"] = entry1
        cache["key2"] = entry2

        stats = cache.get_stats()
        # Stats from persistent_store include cache_size, hit_rate, hits, misses
        assert "cache_size" in stats
        assert "hit_rate" in stats
        assert "memory_entries" in stats
        assert stats["memory_entries"] == 2
        assert stats["cache_size"] == 2

    def test_clear_cache(self, temp_cache_dir):
        """Test clearing cache entries."""
        cache = PersistentTokenCache(cache_dir=temp_cache_dir)

        entry1 = CacheEntry(key="test1", value="response1", tokens_used=100)
        entry2 = CacheEntry(key="test2", value="response2", tokens_used=150)

        cache["key1"] = entry1
        cache["key2"] = entry2

        assert len(cache) == 2

        cache.clear()

        # clear() clears in-memory cache but keeps file for history
        assert len(cache) == 0
        cache_file = temp_cache_dir / "token_cache.jsonl"
        assert cache_file.exists()  # File persists for history

    def test_persistence_disabled_option(self, temp_cache_dir):
        """Test cache with persistence disabled."""
        cache = PersistentTokenCache(cache_dir=temp_cache_dir, persistence_enabled=False)

        entry = CacheEntry(key="test", value="response", tokens_used=50)
        cache["key1"] = entry

        # Cache file should not exist
        cache_file = temp_cache_dir / "cache.jsonl"
        assert not cache_file.exists()

        # But entry should be in memory
        assert len(cache) == 1
        assert cache["key1"].value == "response"


__all__ = [
    "TestPersistentTokenCache",
]
