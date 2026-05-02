"""LRU cache extending PersistentCache with bounded size and automatic eviction.

Implements an Least Recently Used (LRU) eviction policy with automatic cleanup
when cache reaches a specified size threshold, ensuring bounded memory usage
while maximizing hit rates.

Key features:
- Extends PersistentCache for persistence + LRU
- OrderedDict-based LRU tracking
- Automatic eviction at 90% threshold → 80% target
- Hit rate stability monitoring
- Metrics for eviction tracking
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any

from cohezion.swarm.persistent_cache import PersistentCache


logger = logging.getLogger(__name__)


class LRUPersistentCache(PersistentCache):
    """LRU cache with bounded size and persistence.

    Extends PersistentCache with automatic LRU-based eviction when the cache
    reaches specified capacity. Maintains access order for efficient LRU ranking.

    Parameters
    ----------
    max_entries : int
        Maximum number of entries before eviction (default: 1000)
    eviction_threshold : float
        Trigger eviction at this percentage full (default: 0.9 = 90%)
    target_utilization : float
        Target utilization after eviction (default: 0.8 = 80%)
    cache_dir : Path | str
        Directory for cache storage (default: data/cache)
    persistence_enabled : bool
        Whether to persist cache to disk (default: True)
    auto_restore : bool
        Whether to automatically restore cache on init (default: True)
    """

    def __init__(
        self,
        max_entries: int = 1000,
        eviction_threshold: float = 0.9,
        target_utilization: float = 0.8,
        cache_dir: str | Any = "data/cache",
        persistence_enabled: bool = True,
        auto_restore: bool = True,
    ) -> None:
        """Initialize LRU persistent cache."""
        # Initialize LRU-specific attributes BEFORE calling parent init
        # This ensures they're available if parent calls load_from_disk
        self.max_entries = max_entries
        self.eviction_threshold = eviction_threshold
        self.target_utilization = target_utilization
        self._access_order: OrderedDict[str, None] = OrderedDict()
        self._eviction_count = 0
        self._evictions_total_entries = 0
        self.persistence_enabled = persistence_enabled
        self.auto_restore = auto_restore

        # Determine cache file path
        cache_dir_path = Path(cache_dir)
        if persistence_enabled and auto_restore:
            cache_dir_path.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir_path / "lru_cache.jsonl"
        else:
            # Use a non-existent path if persistence is disabled
            # This prevents parent from loading any previous cache
            cache_file = Path(cache_dir_path) / ".no_persist_lru_cache.jsonl"

        # Now initialize parent with cache_file
        # The parent will call load_from_disk() in __init__
        super().__init__(cache_file=str(cache_file), max_entries=max_entries)

        # If persistence is disabled, clear the loaded cache
        if not persistence_enabled:
            self.memory_cache.clear()
            self._stats["loaded"] = 0
            self._access_order.clear()
        else:
            # After parent init, rebuild access order from loaded entries
            self._rebuild_access_order()

    def get(self, key: str) -> Any | None:
        """Get value from cache and update LRU order.

        Parameters
        ----------
        key : str
            Cache key

        Returns
        -------
        Any | None
            Cached value or None if not found
        """
        with self._lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                entry["hits"] = entry.get("hits", 0) + 1
                self._stats["hits"] += 1

                # Move to end (most recently used)
                if key in self._access_order:
                    self._access_order.move_to_end(key)

                return entry.get("value")

            self._stats["misses"] += 1
            return None

    def put(self, key: str, value: Any) -> None:
        """Put value into cache with LRU tracking.

        Automatically evicts least recently used entries if cache
        reaches the eviction threshold.

        Parameters
        ----------
        key : str
            Cache key
        value : Any
            Value to cache
        """
        with self._lock:
            # Check if we're adding a new entry
            is_new_entry = key not in self.memory_cache

            # Put entry using parent class (PersistentCache uses set() not put())
            super().set(key, value)

            # Track access order
            if is_new_entry:
                self._access_order[key] = None
            else:
                # Move existing key to end (most recently used)
                self._access_order.move_to_end(key)

            # Check if eviction is needed
            # Calculate actual utilization from cache size
            current_size = len(self.memory_cache)
            utilization = current_size / self.max_entries

            # Only evict if we actually exceed the eviction threshold
            if utilization > self.eviction_threshold:
                self._evict_lru()

    def delete(self, key: str) -> bool:
        """Delete entry from cache and access order.

        Parameters
        ----------
        key : str
            Cache key

        Returns
        -------
        bool
            True if entry existed and was deleted
        """
        with self._lock:
            # Check if key exists
            if key not in self.memory_cache:
                return False

            # Delete from memory cache
            del self.memory_cache[key]

            # Delete from access order
            self._access_order.pop(key, None)

            return True

    def clear(self) -> None:
        """Clear all entries from cache and access order."""
        with self._lock:
            super().clear()
            self._access_order.clear()
            self._eviction_count = 0
            self._evictions_total_entries = 0

    def _evict_lru(self) -> None:
        """Evict least recently used entries to target utilization.

        Removes entries starting from the oldest (least recently used)
        until cache utilization reaches target_utilization.
        """
        target_size = int(self.max_entries * self.target_utilization)
        current_size = len(self.memory_cache)

        if current_size <= target_size:
            return

        entries_to_evict = current_size - target_size

        logger.info(
            f"LRU eviction: {current_size}/{self.max_entries} entries "
            f"({current_size / self.max_entries * 100:.1f}%). "
            f"Evicting {entries_to_evict} entries to {target_size}/{self.max_entries}"
        )

        evicted_keys = []
        for _ in range(entries_to_evict):
            if not self._access_order:
                break

            # Get least recently used (first in OrderedDict)
            lru_key = next(iter(self._access_order))

            # Remove from both cache and access order
            if lru_key in self.memory_cache:
                del self.memory_cache[lru_key]
                evicted_keys.append(lru_key)

            del self._access_order[lru_key]

        # Update metrics
        if evicted_keys:
            self._eviction_count += 1
            self._evictions_total_entries += len(evicted_keys)

            logger.debug(
                f"Evicted {len(evicted_keys)} LRU entries. "
                f"Cache now at {len(self.memory_cache)}/{self.max_entries} "
                f"({len(self.memory_cache) / self.max_entries * 100:.1f}%)"
            )

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics including LRU metrics.

        Returns
        -------
        dict[str, Any]
            Cache statistics with LRU-specific metrics
        """
        with self._lock:
            base_stats = super().get_stats()

            # Add LRU-specific metrics
            base_stats.update(
                {
                    "max_entries": self.max_entries,
                    "eviction_threshold": self.eviction_threshold,
                    "target_utilization": self.target_utilization,
                    "utilization": len(self.memory_cache) / self.max_entries,
                    "eviction_count": self._eviction_count,
                    "total_evicted_entries": self._evictions_total_entries,
                    "avg_entries_per_eviction": (
                        self._evictions_total_entries / self._eviction_count if self._eviction_count > 0 else 0
                    ),
                }
            )

            return base_stats

    def get_eviction_stats(self) -> dict[str, Any]:
        """Get detailed eviction statistics.

        Returns
        -------
        dict[str, Any]
            Eviction metrics
        """
        with self._lock:
            return {
                "eviction_count": self._eviction_count,
                "total_evicted_entries": self._evictions_total_entries,
                "avg_per_eviction": (
                    self._evictions_total_entries / self._eviction_count if self._eviction_count > 0 else 0
                ),
                "current_utilization": len(self.memory_cache) / self.max_entries,
                "current_size": len(self.memory_cache),
                "max_size": self.max_entries,
            }

    def _rebuild_access_order(self) -> None:
        """Rebuild access order from current cache entries.

        Called after restore to rebuild the LRU ordering.
        """
        with self._lock:
            self._access_order.clear()
            for key in self.memory_cache:
                self._access_order[key] = None

            logger.debug(f"Rebuilt LRU access order for {len(self._access_order)} entries")

    @property
    def eviction_threshold_percent(self) -> float:
        """Get eviction threshold as percentage.

        Returns
        -------
        float
            Eviction threshold percentage (0-100)
        """
        return self.eviction_threshold * 100

    @property
    def target_utilization_percent(self) -> float:
        """Get target utilization as percentage.

        Returns
        -------
        float
            Target utilization percentage (0-100)
        """
        return self.target_utilization * 100

    @property
    def current_utilization_percent(self) -> float:
        """Get current utilization as percentage.

        Returns
        -------
        float
            Current utilization percentage (0-100)
        """
        with self._lock:
            return (len(self.memory_cache) / self.max_entries) * 100
