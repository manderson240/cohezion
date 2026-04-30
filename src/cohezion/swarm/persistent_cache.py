"""PersistentCache - Phase 1 Bottleneck #2: Session persistence and recovery.

JSONL-backed cache that survives process restarts, enabling cross-session
cache reuse and session recovery.

Target: 15% throughput improvement through session restore.
"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached result."""

    key: str
    value: Any
    tokens_used: int = 0
    hits: int = 0
    timestamp: str = ""

    def __post_init__(self):
        """Set default timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class PersistentCache:
    """JSONL-backed cache with automatic session restore.

    Stores cache entries in append-only JSONL format for persistence.
    Loads all entries into memory on startup for fast access.
    Tracks hit counts and timestamps for cache statistics.

    Attributes:
        cache_file: Path to JSONL cache file
        memory_cache: In-memory dict for O(1) lookups
        _lock: Thread lock for safe concurrent access
        _stats: Hit/miss statistics
    """

    def __init__(
        self,
        cache_file: str | Path = "cache_session.jsonl",
        max_entries: int = 10000,
    ):
        """Initialize PersistentCache.

        Args:
            cache_file: Path to JSONL cache file (default: cache_session.jsonl)
            max_entries: Maximum entries to keep in memory (soft limit)
        """
        self.cache_file = Path(cache_file)
        self.max_entries = max_entries
        self.memory_cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._stats = {
            "hits": 0,
            "misses": 0,
            "persisted": 0,
            "loaded": 0,
        }

        # Load existing cache from disk
        self.load_from_disk()

    def load_from_disk(self) -> None:
        """Restore cache from JSONL on startup.

        Reads all entries from JSONL file into memory_cache.
        Non-blocking on errors - missing files are normal for new sessions.
        """
        if not self.cache_file.exists():
            logger.debug(f"Cache file does not exist: {self.cache_file}")
            return

        try:
            with self._lock:
                entries_loaded = 0
                with open(self.cache_file) as f:
                    for line_num, line in enumerate(f, 1):
                        # Skip empty lines
                        if not line.strip():
                            continue

                        try:
                            entry = json.loads(line)
                            cache_key = entry.get("key")
                            if cache_key:
                                self.memory_cache[cache_key] = {
                                    "value": entry.get("value"),
                                    "hits": entry.get("hits", 0),
                                    "timestamp": entry.get("timestamp"),
                                }
                                entries_loaded += 1
                        except json.JSONDecodeError as e:
                            logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")

                self._stats["loaded"] = entries_loaded
                logger.info(
                    (
                        f"Session recovery: loaded {entries_loaded} cache entries from "
                        f"{self.cache_file}"
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")

    def get(self, key: str) -> str | None:
        """Get value from cache (memory).

        Updates hit count and persists hit tracking.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        with self._lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                entry["hits"] = entry.get("hits", 0) + 1
                self._stats["hits"] += 1

                # Persist hit update for analytics
                self._persist_entry(key, entry)
                value = entry.get("value")
                return value if isinstance(value, str) else None

            self._stats["misses"] += 1
            return None

    def set(self, key: str, value: str, persist: bool = True) -> None:
        """Set value in cache (memory + optionally disk).

        Args:
            key: Cache key
            value: Value to cache
            persist: If True, write to JSONL file (default: True)
        """
        with self._lock:
            entry = {
                "key": key,
                "value": value,
                "hits": 0,
                "timestamp": datetime.now().isoformat(),
            }
            self.memory_cache[key] = entry

            if persist:
                self._persist_entry(key, entry)

    def _persist_entry(self, key: str, entry: dict[str, Any]) -> None:
        """Persist single entry to JSONL (append-only).

        Non-blocking on errors - persistence is nice-to-have, not essential.

        Args:
            key: Cache key (for logging)
            entry: Entry dict to persist
        """
        try:
            with open(self.cache_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
            self._stats["persisted"] += 1
        except Exception as e:
            logger.debug(f"Failed to persist cache entry {key}: {e}")

    def batch_set(self, entries: dict[str, str], persist: bool = True) -> int:
        """Set multiple cache entries efficiently.

        Args:
            entries: Dict of {key: value} pairs to cache
            persist: If True, write all to JSONL

        Returns:
            Number of entries set
        """
        count = 0
        with self._lock:
            for key, value in entries.items():
                self.set(key, value, persist=False)  # Don't persist one-by-one
                count += 1

            # Batch persist all entries
            if persist:
                try:
                    with open(self.cache_file, "a") as f:
                        for key, _ in entries.items():
                            if key in self.memory_cache:
                                entry = self.memory_cache[key]
                                f.write(json.dumps(entry) + "\n")
                    self._stats["persisted"] += len(entries)
                except Exception as e:
                    logger.debug(f"Failed to batch persist: {e}")

        return count

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate as percentage (0-100)
        """
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            if total == 0:
                return 0.0
            return (self._stats["hits"] / total) * 100.0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hit/miss counts, hit rate, and persistence stats
        """
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0

            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "total_accesses": total,
                "hit_rate": hit_rate,
                "cache_size": len(self.memory_cache),
                "persisted_entries": self._stats["persisted"],
                "loaded_entries": self._stats["loaded"],
                "cache_file": str(self.cache_file),
            }

    def clear(self) -> None:
        """Clear in-memory cache (does NOT delete JSONL file).

        Use when you want to reset the session but keep history.
        """
        with self._lock:
            self.memory_cache.clear()
            logger.info("In-memory cache cleared")

    def clear_all(self) -> None:
        """Clear in-memory cache AND delete JSONL file.

        Use for hard reset or cleanup.
        """
        with self._lock:
            self.memory_cache.clear()
            if self.cache_file.exists():
                try:
                    self.cache_file.unlink()
                    logger.info(f"Cleared cache file: {self.cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete cache file: {e}")

    def size(self) -> int:
        """Get current cache size (in-memory entries).

        Returns:
            Number of cached entries
        """
        with self._lock:
            return len(self.memory_cache)

    def cache_file_size_mb(self) -> float:
        """Get JSONL file size in MB.

        Returns:
            File size in megabytes
        """
        if self.cache_file.exists():
            return self.cache_file.stat().st_size / (1024 * 1024)
        return 0.0

    def entries(self) -> list[tuple[str, dict[str, Any]]]:
        """Get all cache entries as (key, value) tuples.

        Returns:
            List of (key, entry_dict) tuples
        """
        with self._lock:
            return list(self.memory_cache.items())


# Module-level singleton
_persistent_cache_instance: PersistentCache | None = None


def get_persistent_cache(
    cache_file: str | Path = "cache_session.jsonl",
    reset: bool = False,
) -> PersistentCache:
    """Get or create PersistentCache singleton.

    Args:
        cache_file: Path to JSONL cache file
        reset: If True, create new instance

    Returns:
        PersistentCache instance
    """
    global _persistent_cache_instance

    if reset or _persistent_cache_instance is None:
        _persistent_cache_instance = PersistentCache(cache_file=cache_file)

    return _persistent_cache_instance


__all__ = [
    "PersistentCache",
    "get_persistent_cache",
]
