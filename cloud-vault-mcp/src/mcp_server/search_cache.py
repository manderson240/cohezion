"""Caching layer for vault search results with TTL and invalidation."""

import hashlib
import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any


logger = logging.getLogger(__name__)


class SearchCache:
    """Thread-safe search result cache with TTL-based expiration.

    Features:
    - Automatic expiration after TTL seconds
    - Manual invalidation for specific cache keys or entire cache
    - Thread-safe operations
    - Memory-efficient with timestamp tracking
    """

    def __init__(self, ttl_seconds: float = 60):
        """Initialize cache with TTL.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            # Check expiration
            age = datetime.now(UTC) - self._timestamps[key]
            if age > self._ttl:
                del self._cache[key]
                del self._timestamps[key]
                self._misses += 1
                return None

            self._hits += 1
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = datetime.now(UTC)

    def invalidate(self, key: str) -> bool:
        """Remove specific cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was present, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all cache entries starting with prefix.

        Args:
            prefix: Prefix to match

        Returns:
            Number of entries removed
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
                del self._timestamps[key]
            return len(keys_to_remove)

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._timestamps.clear()
            return count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0

            # Count expired entries
            now = datetime.now(UTC)
            expired_count = sum(
                1 for ts in self._timestamps.values() if (now - ts) > self._ttl
            )

            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "expired_entries": expired_count,
                "ttl_seconds": self._ttl.total_seconds(),
            }

    def reset_stats(self) -> None:
        """Reset hit/miss counters."""
        with self._lock:
            self._hits = 0
            self._misses = 0

    @staticmethod
    def generate_key(query: str, scope: str = "all", folder: str = "") -> str:
        """Generate cache key from search parameters.

        Args:
            query: Search query
            scope: Search scope (all, folder, tags)
            folder: Folder path (if scope=folder)

        Returns:
            Hash-based cache key
        """
        key_parts = f"{query}:{scope}:{folder}"
        return hashlib.md5(key_parts.encode()).hexdigest()
