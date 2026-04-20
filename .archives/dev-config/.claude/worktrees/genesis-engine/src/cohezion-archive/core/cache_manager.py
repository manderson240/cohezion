"""
Simple cache manager for COHEZION system.
"""

import time
from typing import Any


class CacheManager:
    """Simple in-memory cache manager with TTL support."""

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a cache value with optional TTL."""
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl if ttl else None,
        }

    def get(self, key: str) -> Any:
        """Get a cache value if not expired."""
        if key not in self._cache:
            return None

        item = self._cache[key]
        if item["expires_at"] and time.time() > item["expires_at"]:
            del self._cache[key]
            return None

        return item["value"]

    def delete(self, key: str) -> None:
        """Delete a cache entry."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
