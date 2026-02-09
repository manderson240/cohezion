"""Test suite for PersistentCache with JSONL persistence."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cohezion.swarm.persistent_cache import CacheEntry, PersistentCache


@pytest.fixture
def temp_cache_dir():
    """Create temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(key="test-key", value="test-value")
        assert entry.key == "test-key"
        assert entry.value == "test-value"
        assert entry.hits == 0

    def test_entry_serialization(self):
        """Test serializing entry to dictionary."""
        entry = CacheEntry(key="test-key", value={"data": "test"}, hits=5)
        data = entry.to_dict()

        assert data["key"] == "test-key"
        assert data["value"] == {"data": "test"}
        assert data["hits"] == 5
        assert "timestamp" in data

    def test_entry_deserialization(self):
        """Test deserializing entry from dictionary."""
        data = {
            "key": "test-key",
            "value": "test-value",
            "hits": 3,
            "timestamp": "2026-02-08T00:00:00",
            "last_accessed": "2026-02-08T00:00:00",
        }
        entry = CacheEntry.from_dict(data)

        assert entry.key == "test-key"
        assert entry.value == "test-value"
        assert entry.hits == 3


class TestPersistentCacheBasics:
    """Test basic cache operations."""

    def test_cache_creation(self, temp_cache_dir):
        """Test creating cache instance."""
        cache = PersistentCache(cache_dir=temp_cache_dir)
        assert cache.size() == 0
        assert cache.get_hit_rate() == 0.0

    def test_cache_put_get(self, temp_cache_dir):
        """Test putting and getting values."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size() == 1

    def test_cache_miss(self, temp_cache_dir):
        """Test cache miss returns None."""
        cache = PersistentCache(cache_dir=temp_cache_dir)
        assert cache.get("nonexistent") is None

    def test_cache_delete(self, temp_cache_dir):
        """Test deleting cache entries."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        cache.put("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.delete("key1") is False
        assert cache.size() == 0

    def test_cache_clear(self, temp_cache_dir):
        """Test clearing all cache entries."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0


class TestPersistentCacheMetrics:
    """Test cache statistics and metrics."""

    def test_hit_rate_calculation(self, temp_cache_dir):
        """Test cache hit rate calculation."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        cache.put("key1", "value1")

        # 3 hits, 2 misses = 3/5 = 0.6
        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("nonexistent")  # miss
        cache.get("nonexistent2")  # miss

        assert cache.get_hit_rate() == 0.6

    def test_cache_stats(self, temp_cache_dir):
        """Test cache statistics."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["entries"] == 2
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["write_count"] == 2

    def test_cache_size_estimation(self, temp_cache_dir):
        """Test cache size estimation."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        cache.put("key1", "a" * 100)
        cache.put("key2", "b" * 200)

        size = cache.get_stats()["cache_size_bytes"]
        assert size > 0


class TestPersistentCacheJSONLPersistence:
    """Test JSONL persistence and session restore."""

    def test_persistence_disabled(self, temp_cache_dir):
        """Test cache with persistence disabled."""
        cache = PersistentCache(
            cache_dir=temp_cache_dir, persistence_enabled=False
        )

        cache.put("key1", "value1")
        assert cache.size() == 1

        # Cache file should not exist
        cache_file = temp_cache_dir / "cache.jsonl"
        assert not cache_file.exists()

    def test_persistence_enabled(self, temp_cache_dir):
        """Test cache with persistence enabled."""
        cache = PersistentCache(
            cache_dir=temp_cache_dir, persistence_enabled=True
        )

        cache.put("key1", "value1")
        cache.put("key2", {"nested": "data"})

        # Cache file should exist
        cache_file = temp_cache_dir / "cache.jsonl"
        assert cache_file.exists()

        # Verify JSONL format
        with open(cache_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 2
            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])
            assert data1["key"] == "key1"
            assert data2["key"] == "key2"

    def test_session_restore(self, temp_cache_dir):
        """Test restoring cache from previous session."""
        # Session 1: Create cache and add entries
        cache1 = PersistentCache(cache_dir=temp_cache_dir, persistence_enabled=True)
        cache1.put("key1", "value1")
        cache1.put("key2", {"data": "value2"})
        assert cache1.size() == 2

        # Session 2: Create new cache instance and verify restore
        cache2 = PersistentCache(
            cache_dir=temp_cache_dir,
            persistence_enabled=True,
            auto_restore=True,
        )
        assert cache2.size() == 2
        assert cache2.get("key1") == "value1"
        assert cache2.get("key2") == {"data": "value2"}

    def test_auto_restore_disabled(self, temp_cache_dir):
        """Test cache with auto_restore disabled."""
        cache1 = PersistentCache(cache_dir=temp_cache_dir, persistence_enabled=True)
        cache1.put("key1", "value1")

        # Create new cache without auto restore
        cache2 = PersistentCache(
            cache_dir=temp_cache_dir,
            persistence_enabled=True,
            auto_restore=False,
        )
        assert cache2.size() == 0


class TestPersistentCacheThreadSafety:
    """Test thread safety of cache operations."""

    def test_concurrent_puts(self, temp_cache_dir):
        """Test concurrent put operations."""
        import threading

        cache = PersistentCache(cache_dir=temp_cache_dir)

        def put_entries(prefix, count):
            for i in range(count):
                key = f"{prefix}-{i}"
                cache.put(key, f"value-{i}")

        threads = [
            threading.Thread(target=put_entries, args=("thread1", 10)),
            threading.Thread(target=put_entries, args=("thread2", 10)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cache.size() == 20

    def test_concurrent_gets(self, temp_cache_dir):
        """Test concurrent get operations."""
        import threading

        cache = PersistentCache(cache_dir=temp_cache_dir)
        cache.put("shared-key", "shared-value")

        results = []

        def get_value():
            results.append(cache.get("shared-key"))

        threads = [threading.Thread(target=get_value) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(v == "shared-value" for v in results)


class TestPersistentCacheEdgeCases:
    """Test edge cases and error handling."""

    def test_complex_value_types(self, temp_cache_dir):
        """Test caching complex data types."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        # List
        cache.put("list", [1, 2, 3])
        assert cache.get("list") == [1, 2, 3]

        # Dict with nested structure
        data = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        cache.put("complex", data)
        assert cache.get("complex") == data

        # Tuple (stored as tuple since we don't JSON serialize in-memory)
        cache.put("tuple", (1, 2, 3))
        result = cache.get("tuple")
        assert result == (1, 2, 3)

    def test_empty_cache_statistics(self, temp_cache_dir):
        """Test statistics on empty cache."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        stats = cache.get_stats()
        assert stats["entries"] == 0
        assert stats["hit_count"] == 0
        assert stats["hit_rate"] == 0.0

    def test_cache_entries_listing(self, temp_cache_dir):
        """Test listing all cache entries."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        entries = cache.entries()
        assert len(entries) == 2
        assert ("key1", "value1") in entries
        assert ("key2", "value2") in entries

    def test_malformed_cache_file_recovery(self, temp_cache_dir):
        """Test recovery from malformed cache file."""
        cache_file = temp_cache_dir / "cache.jsonl"

        # Write mixed valid and invalid JSONL
        with open(cache_file, "w") as f:
            # Valid entry
            f.write(
                '{"key": "key1", "value": "value1", "hits": 0, "timestamp": "2026-02-08T00:00:00", "last_accessed": "2026-02-08T00:00:00"}\n'
            )
            # Invalid entry
            f.write("invalid json {\n")
            # Another valid entry
            f.write(
                '{"key": "key2", "value": "value2", "hits": 0, "timestamp": "2026-02-08T00:00:00", "last_accessed": "2026-02-08T00:00:00"}\n'
            )

        # Should restore valid entries and skip invalid ones
        cache = PersistentCache(cache_dir=temp_cache_dir, auto_restore=True)
        # Should have restored the two valid entries
        assert cache.size() == 2
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
