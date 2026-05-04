"""LRU-based persistent token cache with automatic eviction and bounded memory.

Extends PersistentTokenCache with automatic LRU eviction to maintain bounded
memory usage while preserving session persistence. This is the Phase 2
integration of LRUPersistentCache (Phase 1 Task #21) with TokenEfficientClient.

Key improvements over PersistentTokenCache:
- Bounded memory: Configurable max_entries with automatic LRU eviction
- Eviction metrics: Track eviction events and effectiveness
- Hit rate stability: Maintain consistent hit rates under memory pressure
- Drop-in replacement: Fully compatible with TokenEfficientClient

Usage::

    # Bounded cache with 500 entries max, evict at 90% utilization
    cache = LRUPersistentTokenCache(
        cache_dir="data/cache",
        max_entries=500,
        eviction_threshold=0.9,
        target_utilization=0.8
    )

    # Use like any dict
    cache[key] = CacheEntry(...)
    entry = cache[key]

    # Get stats including eviction metrics
    stats = cache.get_stats()
    print(f"Evictions: {stats['eviction_count']}")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cohezion.swarm.batch_processor import CacheEntry
from cohezion.swarm.lru_persistent_cache import LRUPersistentCache


logger = logging.getLogger(__name__)


class LRUPersistentTokenCache(dict):
    """Dict-like cache with LRU eviction for TokenEfficientClient.

    Extends dict with JSONL persistence AND LRU eviction for bounded memory.
    Works as a drop-in replacement for TokenEfficientClient's cache.

    Features:
    - Session persistence via JSONL (survives process restarts)
    - Automatic LRU eviction when reaching max_entries
    - Hit rate tracking and eviction metrics
    - Full compatibility with TokenEfficientClient.CacheEntry format

    Parameters
    ----------
    cache_dir : Path | str
        Directory for cache storage (default: data/cache)
    max_entries : int
        Maximum number of entries before eviction (default: 500)
    eviction_threshold : float
        Trigger eviction at this percentage full (default: 0.9 = 90%)
    target_utilization : float
        Target utilization after eviction (default: 0.8 = 80%)
    persistence_enabled : bool
        Whether to persist to disk (default: True)
    auto_restore : bool
        Whether to restore from disk on init (default: True)
    """

    def __init__(
        self,
        cache_dir: Path | str = "data/cache",
        max_entries: int = 500,
        eviction_threshold: float = 0.9,
        target_utilization: float = 0.8,
        persistence_enabled: bool = True,
        auto_restore: bool = True,
    ) -> None:
        """Initialize LRU persistent token cache."""
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.max_entries = max_entries
        self.persistence_enabled = persistence_enabled

        # Initialize underlying LRUPersistentCache (Phase 1 Task #21)
        self.lru_store = LRUPersistentCache(
            max_entries=max_entries,
            eviction_threshold=eviction_threshold,
            target_utilization=target_utilization,
            cache_dir=str(cache_dir),
            persistence_enabled=persistence_enabled,
            auto_restore=auto_restore,
        )

        # Restore entries from persistent storage into memory
        if auto_restore:
            self._restore_entries_from_store()

    def _restore_entries_from_store(self) -> None:
        """Restore CacheEntry objects from LRU persistent store."""
        # Restore from the in-memory cache of LRUPersistentCache
        for key, cached_value in self.lru_store.memory_cache.items():
            # cached_value has: value (JSON string), hits, timestamp
            try:
                # The value field contains JSON-encoded data
                if isinstance(cached_value.get("value"), str):
                    entry_data = json.loads(cached_value["value"])
                else:
                    entry_data = cached_value.get("value", {})

                # Reconstruct CacheEntry from stored data
                # Note: batch_processor.CacheEntry only takes key, value, tokens_used
                entry = CacheEntry(
                    key=entry_data.get("key", key),
                    value=entry_data.get("value"),
                    tokens_used=entry_data.get("tokens_used", 0),
                )
                super().__setitem__(key, entry)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to restore cache entry {key}: {e}")

    def __setitem__(self, key: str, value: Any) -> None:
        """Set cache entry and persist to disk with LRU tracking.

        Parameters
        ----------
        key : str
            Cache key
        value : CacheEntry
            Cache entry to store
        """
        # Track if this is a new entry
        _is_new_entry = key not in self

        # Store in memory dict
        super().__setitem__(key, value)

        # Persist to disk with LRU tracking if persistence is enabled
        if self.persistence_enabled and isinstance(value, CacheEntry):
            # Store as JSON string - LRUPersistentCache expects string values
            persistent_value = json.dumps(
                {
                    "key": value.key,
                    "value": value.value,
                    "tokens_used": value.tokens_used,
                }
            )
            self.lru_store.put(key, persistent_value)

            # If LRU store evicted entries, mirror that in memory dict
            # Check if our in-memory dict has grown larger than LRU store
            # and remove entries that aren't in LRU store
            if len(self) > len(self.lru_store.memory_cache):
                # Sync memory dict with LRU store
                keys_to_remove = [k for k in self.keys() if k not in self.lru_store.memory_cache]
                for k in keys_to_remove:
                    super().__delitem__(k)

    def __getitem__(self, key: str) -> Any:
        """Get cache entry from memory."""
        return super().__getitem__(key)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics including LRU metrics.

        Returns
        -------
        dict[str, Any]
            Cache statistics including:
            - Standard stats: hit_rate, cache_size, etc.
            - LRU stats: eviction_count, total_evicted, utilization
        """
        lru_stats = self.lru_store.get_stats()
        stats = {
            "memory_entries": len(self),
            "max_entries": self.max_entries,
            "utilization": len(self) / self.max_entries if self.max_entries > 0 else 0,
            "hit_rate": lru_stats.get("hit_rate", 0),
            "hits": lru_stats.get("hits", 0),
            "misses": lru_stats.get("misses", 0),
            "total_operations": lru_stats.get("total_accesses", 0),
            "eviction_count": lru_stats.get("eviction_count", 0),
            "total_evicted_entries": lru_stats.get("total_evicted_entries", 0),
        }
        return stats

    def get_hit_rate(self) -> float:
        """Get cache hit rate.

        Returns
        -------
        float
            Hit rate as decimal (0.0 to 1.0)
        """
        stats = self.lru_store.get_stats()
        return stats.get("hit_rate", 0.0) / 100.0

    def get_eviction_stats(self) -> dict[str, Any]:
        """Get detailed eviction statistics.

        Returns
        -------
        dict[str, Any]
            Eviction metrics including count, total evicted, current utilization
        """
        return self.lru_store.get_eviction_stats()

    def clear(self) -> None:
        """Clear all cache entries."""
        super().clear()
        self.lru_store.clear()


__all__ = [
    "LRUPersistentTokenCache",
]
