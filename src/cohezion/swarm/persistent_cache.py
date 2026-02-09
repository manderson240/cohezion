"""Persistent cache with JSONL persistence and session restore.

Provides a simple, session-aware cache that persists entries to disk
and restores them on startup, improving cache hit rates across sessions.

Key features:
- JSONL format for easy inspection and recovery
- Automatic session restore on init
- Hit rate tracking with metadata
- Thread-safe operations
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""

    key: str
    value: Any
    hits: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "hits": self.hits,
            "timestamp": self.timestamp,
            "last_accessed": self.last_accessed,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CacheEntry:
        """Create entry from dictionary."""
        return CacheEntry(
            key=data["key"],
            value=data["value"],
            hits=data.get("hits", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            last_accessed=data.get("last_accessed", datetime.now().isoformat()),
        )


class PersistentCache:
    """Session-aware cache with JSONL persistence.

    Stores cache entries to disk in JSONL format and automatically
    restores them on startup, enabling persistent cache across sessions.

    Parameters
    ----------
    cache_dir : Path | str
        Directory for cache storage (default: data/cache)
    persistence_enabled : bool
        Whether to persist cache to disk (default: True)
    auto_restore : bool
        Whether to automatically restore cache on init (default: True)
    """

    def __init__(
        self,
        cache_dir: Path | str = "data/cache",
        persistence_enabled: bool = True,
        auto_restore: bool = True,
    ) -> None:
        """Initialize persistent cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "cache.jsonl"
        self._persistence_enabled = persistence_enabled
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._hit_count = 0
        self._miss_count = 0
        self._write_count = 0

        # Create cache directory if it doesn't exist
        if self._persistence_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Restore cache from disk on startup
        if auto_restore and self._persistence_enabled:
            self._restore_from_disk()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

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
            entry = self._cache.get(key)
            if entry is not None:
                entry.hits += 1
                entry.last_accessed = datetime.now().isoformat()
                self._hit_count += 1
                logger.debug(f"Cache hit for key={key} (hits={entry.hits})")
                return entry.value
            else:
                self._miss_count += 1
                logger.debug(f"Cache miss for key={key}")
                return None

    def put(self, key: str, value: Any) -> None:
        """Put value into cache and persist.

        Parameters
        ----------
        key : str
            Cache key
        value : Any
            Value to cache
        """
        with self._lock:
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=datetime.now().isoformat(),
                last_accessed=datetime.now().isoformat(),
            )
            self._cache[key] = entry
            self._write_count += 1

            # Persist to disk if enabled
            if self._persistence_enabled:
                self._append_to_disk(entry)

            logger.debug(f"Cached key={key} (total entries={len(self._cache)})")

    def delete(self, key: str) -> bool:
        """Delete entry from cache.

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
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted key={key} from cache")
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            if self._persistence_enabled:
                self.cache_file.unlink(missing_ok=True)
            logger.info("Cleared all cache entries")

    def get_hit_rate(self) -> float:
        """Get cache hit rate.

        Returns
        -------
        float
            Hit rate as decimal (0.0 to 1.0)
        """
        with self._lock:
            total = self._hit_count + self._miss_count
            if total == 0:
                return 0.0
            return self._hit_count / total

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns
        -------
        dict[str, Any]
            Cache statistics including hit rate, size, etc.
        """
        with self._lock:
            total_requests = self._hit_count + self._miss_count
            return {
                "entries": len(self._cache),
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "total_requests": total_requests,
                "hit_rate": self.get_hit_rate(),
                "write_count": self._write_count,
                "cache_size_bytes": self._estimate_size(),
            }

    def _estimate_size(self) -> int:
        """Estimate cache size in bytes.

        Returns
        -------
        int
            Estimated size in bytes
        """
        total = 0
        for entry in self._cache.values():
            # Rough estimate: key + value + metadata
            total += len(entry.key) + len(json.dumps(entry.value)) + 100
        return total

    def _restore_from_disk(self) -> None:
        """Restore cache from JSONL file.

        Loads all entries from cache.jsonl file into memory.
        Gracefully skips malformed entries.
        """
        if not self.cache_file.exists():
            logger.debug(f"No cache file found at {self.cache_file}")
            return

        restored_count = 0
        try:
            with open(self.cache_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        entry = CacheEntry.from_dict(data)
                        self._cache[entry.key] = entry
                        restored_count += 1
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(
                            f"Skipped malformed cache entry at line {line_num}: {e}"
                        )
                        continue

            logger.info(
                f"Restored {restored_count} entries from {self.cache_file}"
            )
        except Exception as e:
            logger.error(f"Failed to restore cache from disk: {e}")

    def _append_to_disk(self, entry: CacheEntry) -> None:
        """Append entry to JSONL file.

        Parameters
        ----------
        entry : CacheEntry
            Cache entry to persist
        """
        try:
            with open(self.cache_file, "a") as f:
                json.dump(entry.to_dict(), f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to persist cache entry: {e}")

    def entries(self) -> list[tuple[str, Any]]:
        """Get all cache entries.

        Returns
        -------
        list[tuple[str, Any]]
            List of (key, value) tuples
        """
        with self._lock:
            return [(key, entry.value) for key, entry in self._cache.items()]

    def size(self) -> int:
        """Get number of entries in cache.

        Returns
        -------
        int
            Number of cached entries
        """
        with self._lock:
            return len(self._cache)
