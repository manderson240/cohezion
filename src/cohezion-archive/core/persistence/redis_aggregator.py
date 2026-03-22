"""Stub for Redis aggregator — real Redis integration was removed.

Provides a no-op RedisAggregator so that SemanticCache can import cleanly
and fall back to local-only vector search.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


class RedisAggregator:
    """No-op Redis client that silently drops all operations."""

    async def connect(self) -> bool:
        return False

    async def get(self, key: str) -> Any:
        return None

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        pass

    async def close(self) -> None:
        pass


_instance: RedisAggregator | None = None


def get_redis() -> RedisAggregator:
    """Return a singleton no-op Redis aggregator."""
    global _instance
    if _instance is None:
        _instance = RedisAggregator()
    return _instance
