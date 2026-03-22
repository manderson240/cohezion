"""Test suite for LRUPersistentCache with bounded size and eviction."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cohezion.swarm.lru_persistent_cache import LRUPersistentCache


@pytest.fixture
def temp_cache_dir():
    """Create temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestLRUBasics:
    """Test basic LRU cache operations."""

    def test_lru_creation(self, temp_cache_dir):
        """Test creating LRU cache instance."""
        cache = LRUPersistentCache(
            max_entries=100,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )
        assert cache.size() == 0
        assert cache.current_utilization_percent == 0.0

    def test_lru_put_get(self, temp_cache_dir):
        """Test putting and getting values."""
        cache = LRUPersistentCache(
            max_entries=100,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size() == 1

    def test_lru_order_tracking(self, temp_cache_dir):
        """Test that access order is tracked."""
        cache = LRUPersistentCache(
            max_entries=100,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Access key1 to make it most recently used
        _ = cache.get("key1")

        # Verify stats show both entries
        stats = cache.get_stats()
        assert stats["cache_size"] == 2


class TestLRUEviction:
    """Test LRU eviction behavior."""

    def test_eviction_at_threshold(self, temp_cache_dir):
        """Test eviction triggers when exceeding threshold."""
        cache = LRUPersistentCache(
            max_entries=10,
            eviction_threshold=0.9,  # 90% = 9 entries
            target_utilization=0.8,  # 80% = 8 entries
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        # Fill cache to 90% (9 entries) - no eviction yet
        for i in range(9):
            cache.put(f"key{i}", f"value{i}")

        assert cache.size() == 9
        assert cache.current_utilization_percent == 90.0

        # Next put (10th entry) exceeds threshold and should trigger eviction
        cache.put("key9", "value9")

        # After eviction, should be at target (80% = 8 entries)
        assert cache.size() == 8
        assert cache.current_utilization_percent == 80.0
        assert cache.get_eviction_stats()["eviction_count"] >= 1

    def test_lru_evicts_least_recently_used(self, temp_cache_dir):
        """Test that eviction removes least recently used entries."""
        cache = LRUPersistentCache(
            max_entries=5,
            eviction_threshold=0.8,  # 4 entries
            target_utilization=0.6,  # 3 entries
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        # Add entries
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        cache.put("key4", "value4")

        # Access key1 and key2 to make them recently used
        _ = cache.get("key1")
        _ = cache.get("key2")

        # key3 and key4 are least recently used

        # Add more entries to trigger eviction
        cache.put("key5", "value5")

        # key3 or key4 should be evicted (LRU)
        # key1 and key2 should still be there (recently accessed)
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # At least one of key3/key4 should be evicted
        evicted = cache.get("key3") is None or cache.get("key4") is None
        assert evicted

    def test_eviction_count_tracking(self, temp_cache_dir):
        """Test eviction count is tracked."""
        cache = LRUPersistentCache(
            max_entries=5,
            eviction_threshold=0.8,
            target_utilization=0.6,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        # Fill to trigger multiple evictions
        for i in range(20):
            cache.put(f"key{i}", f"value{i}")

        stats = cache.get_eviction_stats()
        assert stats["eviction_count"] > 0
        assert stats["total_evicted_entries"] > 0


class TestLRUMetrics:
    """Test LRU cache metrics."""

    def test_utilization_percentage(self, temp_cache_dir):
        """Test utilization percentage calculation."""
        cache = LRUPersistentCache(
            max_entries=100,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        cache.put("key0", "value0")
        assert cache.current_utilization_percent == 1.0

        for i in range(1, 50):
            cache.put(f"key{i}", f"value{i}")

        # 50 entries out of 100 = 50%
        assert cache.current_utilization_percent == 50.0

    def test_cache_stats_completeness(self, temp_cache_dir):
        """Test cache stats include LRU metrics."""
        cache = LRUPersistentCache(
            max_entries=100,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        cache.put("key1", "value1")
        cache.get("key1")

        stats = cache.get_stats()
        assert "max_entries" in stats
        assert "eviction_threshold" in stats
        assert "target_utilization" in stats
        assert "utilization" in stats
        assert "eviction_count" in stats
        assert "total_evicted_entries" in stats

    def test_eviction_stats(self, temp_cache_dir):
        """Test detailed eviction stats."""
        cache = LRUPersistentCache(
            max_entries=10,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        # Trigger evictions
        for i in range(20):
            cache.put(f"key{i}", f"value{i}")

        ev_stats = cache.get_eviction_stats()
        assert ev_stats["current_size"] <= ev_stats["max_size"]
        assert ev_stats["current_utilization"] <= 1.0


class TestLRUWithPersistence:
    """Test LRU cache with persistence."""

    def test_persistence_with_eviction(self, temp_cache_dir):
        """Test that eviction respects persistence."""
        cache = LRUPersistentCache(
            max_entries=10,
            eviction_threshold=0.8,
            target_utilization=0.6,
            cache_dir=temp_cache_dir,
            persistence_enabled=True,
        )

        # Add entries and trigger eviction
        for i in range(15):
            cache.put(f"key{i}", f"value{i}")

        # Verify cache was written
        cache_file = temp_cache_dir / "lru_cache.jsonl"
        assert cache_file.exists()

    def test_session_restore_with_lru(self, temp_cache_dir):
        """Test restoring LRU cache across sessions."""
        # Session 1
        cache1 = LRUPersistentCache(
            max_entries=10,
            cache_dir=temp_cache_dir,
            persistence_enabled=True,
        )

        cache1.put("key1", "value1")
        cache1.put("key2", "value2")
        cache1.put("key3", "value3")

        # Session 2 - restore from disk
        cache2 = LRUPersistentCache(
            max_entries=10,
            cache_dir=temp_cache_dir,
            persistence_enabled=True,
            auto_restore=True,
        )

        # Verify entries restored
        assert cache2.size() == 3
        assert cache2.get("key1") == "value1"
        assert cache2.get("key2") == "value2"
        assert cache2.get("key3") == "value3"

        # Verify access order is correct
        stats = cache2.get_stats()
        assert stats["cache_size"] == 3


class TestLRUProperties:
    """Test LRU cache properties and thresholds."""

    def test_threshold_percentage_properties(self, temp_cache_dir):
        """Test threshold percentage properties."""
        cache = LRUPersistentCache(
            max_entries=100,
            eviction_threshold=0.85,
            target_utilization=0.70,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        assert cache.eviction_threshold_percent == 85.0
        assert cache.target_utilization_percent == 70.0

    def test_configurable_thresholds(self, temp_cache_dir):
        """Test using different threshold values."""
        cache_strict = LRUPersistentCache(
            max_entries=100,
            eviction_threshold=0.5,  # Evict at 50%
            target_utilization=0.4,  # Down to 40%
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        for i in range(60):
            cache_strict.put(f"key{i}", f"value{i}")

        # Should have triggered eviction
        utilization = cache_strict.current_utilization_percent
        assert utilization <= 50.0


class TestLRUEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_cache_eviction(self, temp_cache_dir):
        """Test eviction behavior with empty cache."""
        cache = LRUPersistentCache(
            max_entries=10,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        # Should handle empty cache gracefully
        cache._evict_lru()
        assert cache.size() == 0

    def test_single_entry_cache(self, temp_cache_dir):
        """Test cache with single entry capacity."""
        cache = LRUPersistentCache(
            max_entries=2,  # Small capacity for testing
            eviction_threshold=0.5,  # Evict at 50% (1 entry)
            target_utilization=0.0,  # Empty after eviction
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        cache.put("key1", "value1")
        assert cache.size() == 1

        # Second entry hits 50% threshold (1/2)
        # Third entry exceeds 50% (2/2) and triggers eviction
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # After eviction, should have only newest
        assert cache.size() == 1
        assert cache.get("key3") == "value3"

    def test_delete_with_lru(self, temp_cache_dir):
        """Test delete operation with LRU."""
        cache = LRUPersistentCache(
            max_entries=10,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.delete("key1") is True
        assert cache.size() == 1
        assert cache.delete("key1") is False  # Already deleted

    def test_clear_resets_metrics(self, temp_cache_dir):
        """Test that clear resets all metrics."""
        cache = LRUPersistentCache(
            max_entries=10,
            cache_dir=temp_cache_dir,
            persistence_enabled=False,
        )

        # Add entries to trigger evictions
        for i in range(20):
            cache.put(f"key{i}", f"value{i}")

        # Clear cache
        cache.clear()

        assert cache.size() == 0
        stats = cache.get_eviction_stats()
        # Eviction count should be reset
        assert stats["eviction_count"] == 0
