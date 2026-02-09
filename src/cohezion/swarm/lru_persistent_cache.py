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
from typing import Any, Optional

from cohezion.swarm.persistent_cache import CacheEntry, PersistentCache

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
        # This ensures they're available if parent calls _restore_from_disk
        self.max_entries = max_entries
        self.eviction_threshold = eviction_threshold
        self.target_utilization = target_utilization
        self._access_order: OrderedDict[str, None] = OrderedDict()
        self._eviction_count = 0
        self._evictions_total_entries = 0

        # Now initialize parent, which may call _restore_from_disk
        super().__init__(
            cache_dir=cache_dir,
            persistence_enabled=persistence_enabled,
            auto_restore=auto_restore,
        )

    def get(self, key: str) -> Optional[Any]:
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
            value = super().get(key)
            if value is not None:
                # Move to end (most recently used)
                self._access_order.move_to_end(key)
            return value

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
            is_new_entry = key not in self._cache

            # Put entry using parent class
            super().put(key, value)

            # Track access order
            if is_new_entry:
                self._access_order[key] = None
            else:
                # Move existing key to end (most recently used)
                self._access_order.move_to_end(key)

            # Check if eviction is needed
            # Calculate actual utilization from cache size
            current_size = len(self._cache)
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
            deleted = super().delete(key)
            if deleted:
                self._access_order.pop(key, None)
            return deleted

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
        current_size = len(self._cache)

        if current_size <= target_size:
            return

        entries_to_evict = current_size - target_size

        logger.info(
            f"LRU eviction: {current_size}/{self.max_entries} entries "
            f"({current_size/self.max_entries*100:.1f}%). "
            f"Evicting {entries_to_evict} entries to {target_size}/{self.max_entries}"
        )

        evicted_keys = []
        for _ in range(entries_to_evict):
            if not self._access_order:
                break

            # Get least recently used (first in OrderedDict)
            lru_key = next(iter(self._access_order))

            # Remove from both cache and access order
            if lru_key in self._cache:
                del self._cache[lru_key]
                evicted_keys.append(lru_key)

            del self._access_order[lru_key]

        # Update metrics
        if evicted_keys:
            self._eviction_count += 1
            self._evictions_total_entries += len(evicted_keys)

            logger.debug(
                f"Evicted {len(evicted_keys)} LRU entries. "
                f"Cache now at {len(self._cache)}/{self.max_entries} "
                f"({len(self._cache)/self.max_entries*100:.1f}%)"
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
                    "utilization": len(self._cache) / self.max_entries,
                    "eviction_count": self._eviction_count,
                    "total_evicted_entries": self._evictions_total_entries,
                    "avg_entries_per_eviction": (
                        self._evictions_total_entries / self._eviction_count
                        if self._eviction_count > 0
                        else 0
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
                    self._evictions_total_entries / self._eviction_count
                    if self._eviction_count > 0
                    else 0
                ),
                "current_utilization": len(self._cache) / self.max_entries,
                "current_size": len(self._cache),
                "max_size": self.max_entries,
            }

    def _restore_from_disk(self) -> None:
        """Restore cache from JSONL and rebuild access order.

        Override parent to also restore access order after loading entries.
        """
        # Call parent restore (without lock, as parent handles it)
        super()._restore_from_disk()

        # Rebuild access order from restored entries
        # Note: parent's _restore_from_disk doesn't use _lock on the whole operation
        for key in self._cache.keys():
            self._access_order[key] = None

        logger.debug(
            f"Rebuilt LRU access order for {len(self._access_order)} entries"
        )

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
            return (len(self._cache) / self.max_entries) * 100
