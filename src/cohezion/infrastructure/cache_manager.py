"""Unified cache infrastructure with tiered architecture.

Pattern: L1 (Memory) → L2 (Semantic) → L3 (File)
All tiers implement CacheBackend interface for composability.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CacheKey:
    """Immutable cache key with metadata."""

    hash: str
    model: str
    prompt: str
    images: tuple[str, ...] = ()

    @classmethod
    def create(
        cls, model: str, prompt: str, images: list[str] | None = None
    ) -> CacheKey:
        content = f"{model}:{prompt}"
        if images:
            content += ":" + ":".join(images[:3])
        return cls(
            hash=hashlib.sha256(content.encode()).hexdigest(),
            model=model,
            prompt=prompt,
            images=tuple(images or ()),
        )


@dataclass(slots=True)
class CacheEntry:
    """Lightweight cache entry with TTL tracking."""

    response: str
    timestamp: float
    ttl_seconds: int
    phi_score: float = 0.0
    confidence: float = 1.0
    alignment_score: float = 1.0
    embedding: list[float] | None = None
    persistence_id: str | None = None
    narration: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: float | None = None) -> bool:
        return (now or time.time()) - self.timestamp > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "timestamp": self.timestamp,
            "ttl_seconds": self.ttl_seconds,
            "phi_score": self.phi_score,
            "confidence": self.confidence,
            "alignment_score": self.alignment_score,
            "embedding": self.embedding,
            "persistence_id": self.persistence_id,
            "narration": self.narration,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        return cls(
            response=data["response"],
            timestamp=data["timestamp"],
            ttl_seconds=data.get("ttl_seconds", 3600),
            phi_score=data.get("phi_score", 0.0),
            confidence=data.get("confidence", 1.0),
            alignment_score=data.get("alignment_score", 1.0),
            embedding=data.get("embedding"),
            persistence_id=data.get("persistence_id"),
            narration=data.get("narration"),
            metadata=data.get("metadata", {}),
        )


class Encoder(Protocol):
    """Protocol for embedding encoders."""

    async def encode(self, text: str) -> list[float]: ...


class CacheBackend(ABC):
    """Abstract base for all cache tiers."""

    @abstractmethod
    async def get(self, key: CacheKey) -> CacheEntry | None:
        """Retrieve entry if available and valid."""
        pass

    @abstractmethod
    async def set(self, key: CacheKey, entry: CacheEntry) -> None:
        """Store entry in cache."""
        pass

    @abstractmethod
    async def clear_expired(self) -> int:
        """Remove expired entries, return count removed."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Return backend statistics."""
        pass


class MemoryBackend(CacheBackend):
    """L1: In-memory LRU cache with size limits."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache: dict[str, CacheEntry] = {}
        self._access_times: dict[str, float] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    async def get(self, key: CacheKey) -> CacheEntry | None:
        now = time.time()
        entry = self._cache.get(key.hash)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired(now):
            del self._cache[key.hash]
            del self._access_times[key.hash]
            self._misses += 1
            return None

        self._access_times[key.hash] = now
        self._hits += 1
        return entry

    async def set(self, key: CacheKey, entry: CacheEntry) -> None:
        # Evict if at capacity (LRU)
        if len(self._cache) >= self._max_size:
            lru_key = min(self._access_times, key=self._access_times.get)
            del self._cache[lru_key]
            del self._access_times[lru_key]

        self._cache[key.hash] = entry
        self._access_times[key.hash] = time.time()

    async def clear_expired(self) -> int:
        now = time.time()
        expired = [k for k, e in self._cache.items() if e.is_expired(now)]
        for k in expired:
            del self._cache[k]
            del self._access_times[k]
        return len(expired)

    async def get_stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "tier": "memory",
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


class FileBackend(CacheBackend):
    """L3: Persistent file-based cache with async I/O."""

    def __init__(self, cache_dir: Path | str, ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    async def get(self, key: CacheKey) -> CacheEntry | None:
        cache_file = self.cache_dir / f"{key.hash}.json"

        if not cache_file.exists():
            self._misses += 1
            return None

        try:
            # Use async file I/O
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, cache_file.read_text)
            entry = CacheEntry.from_dict(json.loads(data))

            if entry.is_expired():
                await loop.run_in_executor(None, cache_file.unlink)
                self._misses += 1
                return None

            self._hits += 1
            return entry

        except Exception as e:
            logger.warning(f"File cache read error for {key.hash[:12]}: {e}")
            self._misses += 1
            return None

    async def set(self, key: CacheKey, entry: CacheEntry) -> None:
        cache_file = self.cache_dir / f"{key.hash}.json"
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: cache_file.write_text(
                    json.dumps(entry.to_dict(), ensure_ascii=False)
                ),
            )
        except Exception as e:
            logger.error(f"File cache write error for {key.hash[:12]}: {e}")

    async def clear_expired(self) -> int:
        removed = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                loop = asyncio.get_event_loop()
                data = json.loads(
                    await loop.run_in_executor(None, cache_file.read_text)
                )
                if now - data.get("timestamp", 0) > data.get(
                    "ttl_seconds", self._ttl_seconds
                ):
                    await loop.run_in_executor(None, cache_file.unlink)
                    removed += 1
            except Exception:
                await loop.run_in_executor(None, cache_file.unlink, True)
                removed += 1

        return removed

    async def get_stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "tier": "file",
            "dir": str(self.cache_dir),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


class SemanticBackend(CacheBackend):
    """L2: Vector similarity cache using SurrealDB."""

    def __init__(
        self,
        encoder: Encoder | None = None,
        db_client: Any | None = None,
        threshold: float = 0.95,
        table_name: str = "semantic_cache",
    ):
        self.encoder = encoder
        self.db_client = db_client
        self.threshold = threshold
        self.table_name = table_name
        self._hits = 0
        self._misses = 0

    async def get(self, key: CacheKey) -> CacheEntry | None:
        if not self.db_client or not self.encoder:
            self._misses += 1
            return None

        try:
            vec = await self.encoder.encode(key.prompt)

            query = f"""
            SELECT *, vector::similarity::cosine(embedding, $vec) as sim
            FROM {self.table_name}
            WHERE embedding <|4|> $vec
            ORDER BY embedding <|4|> $vec ASC
            LIMIT 1;
            """

            result = await self.db_client.query(query, {"vec": vec})

            if isinstance(result, list) and len(result) > 0 and "result" in result[0]:
                rows = result[0]["result"]
            else:
                rows = result

            if not rows:
                self._misses += 1
                return None

            best = rows[0]
            sim = best.get("sim", 0.0)

            if sim >= self.threshold:
                self._hits += 1
                return CacheEntry(
                    response=best["response_content"],
                    timestamp=time.time(),  # Reset TTL on semantic hit
                    ttl_seconds=3600,
                    metadata={
                        "semantic_match": best.get("query_text", ""),
                        "similarity": sim,
                    },
                )

            self._misses += 1
            return None

        except Exception as e:
            logger.error(f"Semantic cache get failed: {e}")
            self._misses += 1
            return None

    async def set(self, key: CacheKey, entry: CacheEntry) -> None:
        if not self.db_client or not self.encoder:
            return

        try:
            vec = await self.encoder.encode(key.prompt)

            record = {
                "query_text": key.prompt,
                "response_content": entry.response,
                "embedding": vec,
                "created_at": datetime.now().isoformat(),
            }

            await self.db_client.create(self.table_name, record)

        except Exception as e:
            logger.error(f"Semantic cache set failed: {e}")

    async def clear_expired(self) -> int:
        # Semantic cache uses DB TTL or manual cleanup
        return 0

    async def get_stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "tier": "semantic",
            "threshold": self.threshold,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


class TieredCacheManager:
    """Unified cache manager with L1→L2→L3 tiered lookup.

    Usage:
        manager = TieredCacheManager()
        await manager.add_backend(MemoryBackend(max_size=1000))
        await manager.add_backend(SemanticBackend(encoder, db))
        await manager.add_backend(FileBackend("cache/swarm"))

        entry = await manager.get("model", "prompt")
        await manager.set("model", "prompt", "response")
    """

    def __init__(self):
        self._backends: list[CacheBackend] = []
        self._stats: dict[str, Any] = {"lookups": 0, "tier_hits": {}}

    async def add_backend(self, backend: CacheBackend) -> None:
        """Add a cache tier (order matters: L1 first, L3 last)."""
        self._backends.append(backend)

    async def get(
        self, model: str, prompt: str, images: list[str] | None = None
    ) -> CacheEntry | None:
        """Tiered lookup: try each backend in order until hit."""
        key = CacheKey.create(model, prompt, images)
        self._stats["lookups"] += 1

        for i, backend in enumerate(self._backends):
            entry = await backend.get(key)
            if entry is not None:
                tier_name = backend.__class__.__name__.replace("Backend", "").lower()
                self._stats["tier_hits"][tier_name] = (
                    self._stats["tier_hits"].get(tier_name, 0) + 1
                )

                # Backfill to faster tiers (cache warming)
                await self._backfill(key, entry, i)
                return entry

        return None

    async def set(
        self,
        model: str,
        prompt: str,
        response: str,
        images: list[str] | None = None,
        ttl_seconds: int = 3600,
        **kwargs,
    ) -> None:
        """Store in all tiers simultaneously."""
        key = CacheKey.create(model, prompt, images)
        entry = CacheEntry(
            response=response, timestamp=time.time(), ttl_seconds=ttl_seconds, **kwargs
        )

        # Write to all tiers in parallel
        await asyncio.gather(
            *[backend.set(key, entry) for backend in self._backends],
            return_exceptions=True,
        )

    async def _backfill(
        self, key: CacheKey, entry: CacheEntry, hit_tier_index: int
    ) -> None:
        """Populate faster tiers when hit in slower tier."""
        for i in range(hit_tier_index):
            try:
                await self._backends[i].set(key, entry)
            except Exception:
                pass

    async def clear_expired(self) -> dict[str, int]:
        """Clear expired entries from all tiers."""
        results = {}
        for backend in self._backends:
            name = backend.__class__.__name__.replace("Backend", "").lower()
            results[name] = await backend.clear_expired()
        return results

    async def get_stats(self) -> dict[str, Any]:
        """Aggregate stats from all tiers."""
        tier_stats = {}
        for backend in self._backends:
            name = backend.__class__.__name__.replace("Backend", "").lower()
            tier_stats[name] = await backend.get_stats()

        return {
            **self._stats,
            "tiers": tier_stats,
        }


# Global singleton for system-wide cache access
_cache_manager: TieredCacheManager | None = None


async def get_cache_manager() -> TieredCacheManager:
    """Get or create the global cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = TieredCacheManager()
    return _cache_manager


def reset_cache_manager() -> None:
    """Reset the global cache manager (for testing)."""
    global _cache_manager
    _cache_manager = None
