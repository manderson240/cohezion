"""Tests for PersistentCache - Phase 1 Bottleneck #2."""

import json
import tempfile
from pathlib import Path

import pytest

from cohezion.swarm.persistent_cache import (
    PersistentCache,
    get_persistent_cache,
)


@pytest.fixture
def temp_cache_file():
    """Create temporary cache file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def cache(temp_cache_file):
    """Create PersistentCache with temporary file."""
    return PersistentCache(cache_file=temp_cache_file)


class TestPersistentCacheInitialization:
    """Test PersistentCache initialization."""

    def test_initialization_new_file(self):
        """Test initialization with new cache file."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            cache_file = Path(f.name)

        cache = PersistentCache(cache_file=cache_file)
        assert cache.cache_file == cache_file
        assert cache.size() == 0
        assert cache.get_hit_rate() == 0.0

        cache_file.unlink()

    def test_initialization_existing_file(self, temp_cache_file):
        """Test initialization loads existing cache."""
        # Pre-populate cache file
        entry1 = {"key": "k1", "value": "v1", "hits": 5, "timestamp": "2026-02-08"}
        entry2 = {"key": "k2", "value": "v2", "hits": 3, "timestamp": "2026-02-08"}

        with open(temp_cache_file, "w") as f:
            f.write(json.dumps(entry1) + "\n")
            f.write(json.dumps(entry2) + "\n")

        # Load cache
        cache = PersistentCache(cache_file=temp_cache_file)
        assert cache.size() == 2
        assert cache.get("k1") == "v1"
        assert cache.get("k2") == "v2"

    def test_initialization_handles_corrupted_lines(self, temp_cache_file):
        """Test initialization skips corrupted JSON lines."""
        # Mix of valid and invalid lines
        with open(temp_cache_file, "w") as f:
            f.write('{"key": "k1", "value": "v1"}\n')
            f.write("invalid json\n")
            f.write('{"key": "k2", "value": "v2"}\n')
            f.write("\n")  # Empty line
            f.write("}\n")  # Invalid

        cache = PersistentCache(cache_file=temp_cache_file)
        assert cache.size() == 2
        assert cache.get("k1") == "v1"
        assert cache.get("k2") == "v2"


class TestCacheOperations:
    """Test cache get/set operations."""

    def test_set_and_get(self, cache):
        """Test basic set and get."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self, cache):
        """Test get on missing key returns None."""
        assert cache.get("missing") is None

    def test_hit_tracking(self, cache):
        """Test hit count tracking."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.get("key1") == "value1"
        assert cache.get("key1") == "value1"

        stats = cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 0

    def test_miss_tracking(self, cache):
        """Test miss count tracking."""
        cache.get("missing1")
        cache.get("missing2")
        cache.get("missing3")

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 3

    def test_hit_rate_calculation(self, cache):
        """Test hit rate percentage calculation."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 2 hits, 1 miss = 66.67%
        cache.get("key1")
        cache.get("key1")
        cache.get("missing")

        hit_rate = cache.get_hit_rate()
        assert 66.0 < hit_rate < 67.0  # ~66.67%


class TestPersistence:
    """Test persistence to JSONL."""

    def test_persist_entry(self, temp_cache_file):
        """Test entry is written to JSONL."""
        cache = PersistentCache(cache_file=temp_cache_file)
        cache.set("key1", "value1")

        # Read file and verify
        with open(temp_cache_file) as f:
            lines = f.readlines()
        assert len(lines) > 0
        entry = json.loads(lines[-1])
        assert entry["key"] == "key1"
        assert entry["value"] == "value1"

    def test_batch_set(self, temp_cache_file):
        """Test batch set writes all entries."""
        cache = PersistentCache(cache_file=temp_cache_file)
        entries = {
            "k1": "v1",
            "k2": "v2",
            "k3": "v3",
        }
        count = cache.batch_set(entries)
        assert count == 3

        # Verify in cache
        assert cache.get("k1") == "v1"
        assert cache.get("k2") == "v2"
        assert cache.get("k3") == "v3"

    def test_session_recovery(self, temp_cache_file):
        """Test cache recovery across sessions."""
        # Session 1: Set entries
        cache1 = PersistentCache(cache_file=temp_cache_file)
        cache1.set("key1", "value1")
        cache1.set("key2", "value2")

        # Session 2: Load from disk
        cache2 = PersistentCache(cache_file=temp_cache_file)
        assert cache2.size() == 2
        assert cache2.get("key1") == "value1"
        assert cache2.get("key2") == "value2"

        stats = cache2.get_stats()
        assert stats["loaded_entries"] == 2


class TestStatistics:
    """Test statistics collection."""

    def test_get_stats(self, cache):
        """Test statistics dictionary."""
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.get("k1")
        cache.get("missing")

        stats = cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "total_accesses" in stats
        assert "hit_rate" in stats
        assert "cache_size" in stats
        assert stats["cache_size"] == 2

    def test_cache_file_size(self, temp_cache_file):
        """Test file size calculation."""
        cache = PersistentCache(cache_file=temp_cache_file)
        cache.set("key1", "value1")

        size_mb = cache.cache_file_size_mb()
        assert size_mb > 0  # Should have some size
        assert size_mb < 1  # But small


class TestClear:
    """Test cache clearing."""

    def test_clear(self, cache):
        """Test clear only removes from memory."""
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0
        assert cache.get("k1") is None

    def test_clear_all(self, temp_cache_file):
        """Test clear_all removes file."""
        cache = PersistentCache(cache_file=temp_cache_file)
        cache.set("k1", "v1")
        assert temp_cache_file.exists()

        cache.clear_all()
        assert not temp_cache_file.exists()
        assert cache.size() == 0


class TestThreadSafety:
    """Test thread safety with locks."""

    def test_concurrent_access(self, cache):
        """Test cache handles concurrent access."""
        import threading

        results = []

        def worker(key_id):
            for i in range(10):
                cache.set(f"key_{key_id}_{i}", f"value_{key_id}_{i}")
                cache.get(f"key_{key_id}_{i}")
            results.append(key_id)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 3
        assert cache.size() > 0


class TestSingletonFactory:
    """Test singleton pattern."""

    def test_get_persistent_cache_singleton(self):
        """Test singleton returns same instance."""
        cache1 = get_persistent_cache()
        cache2 = get_persistent_cache()
        assert cache1 is cache2

    def test_get_persistent_cache_reset(self):
        """Test reset creates new instance."""
        cache1 = get_persistent_cache()
        cache2 = get_persistent_cache(reset=True)
        assert cache1 is not cache2

    def test_get_persistent_cache_custom_file(self):
        """Test custom cache file."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            custom_path = Path(f.name)

        cache = get_persistent_cache(cache_file=custom_path, reset=True)
        assert cache.cache_file == custom_path

        custom_path.unlink()


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, temp_cache_file):
        """Test complete cache workflow."""
        # Session 1
        cache1 = PersistentCache(cache_file=temp_cache_file)
        cache1.batch_set({"k1": "v1", "k2": "v2", "k3": "v3"})

        # Multiple accesses
        for _ in range(3):
            cache1.get("k1")
        cache1.get("missing")

        stats1 = cache1.get_stats()
        assert stats1["hits"] == 3
        assert stats1["misses"] == 1

        # Session 2: Recovery
        cache2 = PersistentCache(cache_file=temp_cache_file)
        assert cache2.size() == 3
        # loaded_entries counts JSONL lines (3 sets + 3 hit updates from cache1)
        stats_before = cache2.get_stats()
        assert stats_before["loaded_entries"] == 6

        # Continue using cache
        cache2.get("k2")
        cache2.get("k3")
        cache2.get("missing2")

        stats2 = cache2.get_stats()
        assert stats2["hits"] == 2
        assert stats2["misses"] == 1
        assert stats2["total_accesses"] == 3

    def test_cache_recovery_performance(self, temp_cache_file):
        """Test session recovery is fast."""
        import time

        # Populate cache
        cache1 = PersistentCache(cache_file=temp_cache_file)
        for i in range(100):
            cache1.set(f"key_{i}", f"value_{i}")

        # Time recovery
        start = time.time()
        cache2 = PersistentCache(cache_file=temp_cache_file)
        recovery_time = time.time() - start

        assert recovery_time < 1.0  # Should load 100 entries in <1s
        assert cache2.size() == 100
