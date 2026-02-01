"""Agent Cache - LRU cache for agent responses with TTL."""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for agent cache."""

    cache_dir: Path | None = None
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 100


@dataclass
class CacheEntry:
    """Cached response entry."""

    response: str
    embedding: list[float] | None
    persistence_id: str | None
    phi_score: float
    confidence: float
    alignment_score: float
    narration: str | None
    timestamp: float
    model: str


class AgentCache:
    """LRU cache for agent responses with TTL-based expiration."""

    def __init__(self, model_name: str, config: CacheConfig | None = None):
        """Initialize agent cache.

        Args:
            model_name: Name of the model for cache key generation.
            config: Cache configuration. Uses defaults if not provided.
        """
        self.model_name = model_name
        self.config = config or CacheConfig()
        self.cache_dir = self.config.cache_dir or Path("cache/swarm")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._cache_hits = 0
        self._cache_misses = 0

    def get(self, key: str, images: list[str] | None = None) -> dict[str, Any] | None:
        """Retrieve a cached response if available and not expired.

        Args:
            key: Cache key string.
            images: Optional list of image paths for hash generation.

        Returns:
            Dictionary with cached data if valid, None otherwise.
        """
        cache_key = self._generate_key(key, images)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            self._cache_misses += 1
            return None

        try:
            with cache_file.open("r") as f:
                data = json.load(f)

            entry = CacheEntry(**data)
            age = time.time() - entry.timestamp

            if age < self.config.cache_ttl_seconds:
                self._cache_hits += 1
                logger.debug(f"Cache hit for key {cache_key[:12]}...")
                return {
                    "response": entry.response,
                    "embedding": entry.embedding,
                    "persistence_id": entry.persistence_id,
                    "phi_score": entry.phi_score,
                    "confidence": entry.confidence,
                    "alignment_score": entry.alignment_score,
                    "narration": entry.narration,
                }
            else:
                logger.debug(f"Cache expired for key {cache_key[:12]}...")
                self._cache_misses += 1
                cache_file.unlink(missing_ok=True)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Cache read error for key {cache_key[:12]}...: {e}")
            self._cache_misses += 1
            cache_file.unlink(missing_ok=True)

        return None

    def set(
        self,
        key: str,
        response: str,
        embedding: list[float] | None = None,
        persistence_id: str | None = None,
        phi_score: float = 0.0,
        confidence: float = 1.0,
        alignment_score: float = 1.0,
        images: list[str] | None = None,
        narration: str | None = None,
    ) -> None:
        """Cache a response with its intelligence metadata.

        Args:
            key: Cache key string.
            response: Response text to cache.
            embedding: Optional embedding vector.
            persistence_id: Optional persistence identifier.
            phi_score: Quality score (0.0 - 1.0).
            confidence: Confidence score (0.0 - 1.0).
            alignment_score: Alignment score (0.0 - 1.0).
            images: Optional list of image paths.
            narration: Optional narration text.
        """
        cache_key = self._generate_key(key, images)
        cache_file = self.cache_dir / f"{cache_key}.json"

        entry = CacheEntry(
            response=response,
            embedding=embedding,
            persistence_id=persistence_id,
            phi_score=phi_score,
            confidence=confidence,
            alignment_score=alignment_score,
            narration=narration,
            timestamp=time.time(),
            model=self.model_name,
        )

        try:
            cache_file.write_text(json.dumps(entry.__dict__, ensure_ascii=False))
            logger.debug(f"Cached response for key {cache_key[:12]}...")
        except Exception as e:
            logger.error(f"Cache write error for key {cache_key[:12]}...: {e}")

    def _generate_key(self, prompt: str, images: list[str] | None = None) -> str:
        """Generate a stable cache key from prompt and images.

        Args:
            prompt: Prompt text.
            images: Optional list of image paths.

        Returns:
            SHA256 hash string.
        """
        content = f"{self.model_name}:{prompt}"
        if images:
            content += ":" + ":".join(images[:3])
        return hashlib.sha256(content.encode()).hexdigest()

    def clear_expired(self) -> int:
        """Remove all expired cache entries.

        Returns:
            Number of entries removed.
        """
        removed = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open("r") as f:
                    data = json.load(f)
                    timestamp = data.get("timestamp", 0)

                if now - timestamp > self.config.cache_ttl_seconds:
                    cache_file.unlink()
                    removed += 1

            except Exception as e:
                logger.warning(f"Error checking cache file {cache_file.name}: {e}")
                cache_file.unlink(missing_ok=True)
                removed += 1

        if removed > 0:
            logger.info(f"Cleared {removed} expired cache entries")

        return removed

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache hit/miss counts and rate.
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "cache_dir": str(self.cache_dir),
        }
