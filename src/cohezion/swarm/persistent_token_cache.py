"""Adapter wrapping PersistentCache for TokenEfficientClient.

Provides a dict-like interface that persists cache entries to disk while
maintaining compatibility with TokenEfficientClient's CacheEntry format.

This enables session restore: kill/restart the process and cache hits resume
immediately without re-processing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cohezion.swarm.batch_processor import CacheEntry
from cohezion.swarm.persistent_cache import PersistentCache


logger = logging.getLogger(__name__)


class PersistentTokenCache(dict):
    """Dict-like cache that persists CacheEntry objects to disk.

    Extends dict with JSONL persistence for TokenEfficientClient compatibility.
    Works as a drop-in replacement for TokenEfficientClient's in-memory cache dict.

    Parameters
    ----------
    cache_dir : Path | str
        Directory for cache storage (default: data/cache)
    persistence_enabled : bool
        Whether to persist to disk (default: True)
    auto_restore : bool
        Whether to restore from disk on init (default: True)
    """

    def __init__(
        self,
        cache_dir: Path | str = "data/cache",
        persistence_enabled: bool = True,
        auto_restore: bool = True,
    ) -> None:
        """Initialize persistent token cache."""
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.persistence_enabled = persistence_enabled

        # Ensure cache directory exists
        if persistence_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / "token_cache.jsonl"
        else:
            cache_file = "token_cache.jsonl"

        self.persistent_store = PersistentCache(cache_file=cache_file)

        # Restore entries from persistent storage into memory
        if auto_restore:
            self._restore_entries_from_store()

    def _restore_entries_from_store(self) -> None:
        """Restore CacheEntry objects from persistent store."""
        # Restore from the in-memory cache of PersistentCache
        for key, cached_value in self.persistent_store.memory_cache.items():
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
        """Set cache entry and persist to disk.

        Parameters
        ----------
        key : str
            Cache key
        value : CacheEntry
            Cache entry to store
        """
        # Store in memory
        super().__setitem__(key, value)

        # Persist to disk if persistence is enabled
        if self.persistence_enabled and isinstance(value, CacheEntry):
            # Store as JSON string - PersistentCache expects string values
            persistent_value = json.dumps(
                {
                    "key": value.key,
                    "value": value.value,
                    "tokens_used": value.tokens_used,
                }
            )
            self.persistent_store.set(key, persistent_value)

    def __getitem__(self, key: str) -> Any:
        """Get cache entry from memory."""
        return super().__getitem__(key)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns
        -------
        dict[str, Any]
            Cache statistics including hit rate, size, etc.
        """
        stats = self.persistent_store.get_stats()
        stats["memory_entries"] = len(self)
        return stats

    def get_hit_rate(self) -> float:
        """Get cache hit rate.

        Returns
        -------
        float
            Hit rate as decimal (0.0 to 1.0)
        """
        return self.persistent_store.get_hit_rate()

    def clear(self) -> None:
        """Clear all cache entries."""
        super().clear()
        self.persistent_store.clear()


__all__ = [
    "PersistentTokenCache",
]
