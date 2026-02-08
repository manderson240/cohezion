"""Multi-tier semantic cache for LLM inference.

Architecture:
    L1: Exact hash matching (FIFO, 512 entries)
    L2: Semantic similarity (cosine >0.92, LFU, 1024 entries)
    L3: Vault lookup (async, non-blocking)

Target: 70%+ cache hit rate with sub-100ms lookup latency.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry."""

    key: str
    prompt: str
    response: str
    embedding: np.ndarray
    timestamp: float = field(default_factory=time.time)
    hit_count: int = 0


class SemanticCache:
    """Multi-tier cache with semantic similarity matching.

    Tiers:
        L1: Exact hash (SHA-256, FIFO, 512 entries)
        L2: Semantic similarity (cosine > threshold, LFU, 1024 entries)
        L3: Vault lookup (async, non-blocking)

    Parameters
    ----------
    similarity_threshold : float
        Cosine similarity threshold for L2 hits (default: 0.92)
    max_l1_size : int
        Maximum L1 cache entries (default: 512)
    max_l2_size : int
        Maximum L2 cache entries (default: 1024)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.92,
        max_l1_size: int = 512,
        max_l2_size: int = 1024,
    ):
        """Initialize semantic cache."""
        self.similarity_threshold = similarity_threshold
        self.max_l1_size = max_l1_size
        self.max_l2_size = max_l2_size

        # L1 cache: exact hash matches
        self.l1_cache: dict[str, CacheEntry] = {}
        self.l1_insertion_order: list[str] = []

        # L2 cache: semantic matches
        self.l2_cache: dict[str, CacheEntry] = {}
        self.l2_lfu_counts: dict[str, int] = {}

        # Stats
        self.hits_l1 = 0
        self.hits_l2 = 0
        self.hits_l3 = 0
        self.misses = 0

    @staticmethod
    def _text_to_embedding(text: str) -> np.ndarray:
        """Convert text to deterministic embedding.

        Uses SHA-256 hash repeated and XOR'd to create 256D vector.
        Normalized for cosine similarity.

        For production, replace with FLUME VAE encoder.

        Args:
            text: Text to embed

        Returns:
            256D numpy array, normalized
        """
        # Hash text
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # Create 256D vector from hash (repeat hash as needed)
        embedding = np.zeros(256, dtype=np.float32)
        for i in range(256):
            byte_idx = i % len(hash_bytes)
            embedding[i] = hash_bytes[byte_idx] / 255.0

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm

        return embedding

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            a: First embedding
            b: Second embedding

        Returns:
            Cosine similarity in [0, 1]
        """
        dot_product = np.dot(a, b)
        return float(dot_product)

    async def get(
        self, prompt: str, system: str | None = None, model: str | None = None
    ) -> str | None:
        """Lookup with 3-tier fallback.

        Checks L1 (exact), L2 (semantic), then L3 (vault).
        Promotes hits to faster tiers.

        Args:
            prompt: Prompt to lookup
            system: System prompt (included in cache key)
            model: Model name (included in cache key)

        Returns:
            Cached response or None if miss
        """
        full_prompt = f"{system or ''}\n{prompt}\n{model or ''}"
        hash_key = hashlib.sha256(full_prompt.encode()).hexdigest()[:16]

        # L1: Exact match
        if hash_key in self.l1_cache:
            entry = self.l1_cache[hash_key]
            self.hits_l1 += 1
            return entry.response

        # L2: Semantic similarity
        query_embedding = self._text_to_embedding(prompt)
        best_match = None
        best_similarity = 0.0

        for _key, entry in self.l2_cache.items():
            similarity = self._cosine_similarity(query_embedding, entry.embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = entry

        if best_match and best_similarity > self.similarity_threshold:
            self.hits_l2 += 1
            # Promote to L1
            self._promote_to_l1(hash_key, best_match)
            return best_match.response

        # L3: Vault lookup (async, non-blocking)
        # TODO: Wire to cohezion.core.mcp_client.MCPClient for vault search
        # For now, always miss
        pass

        self.misses += 1
        return None

    async def put(
        self,
        prompt: str,
        response: str,
        system: str | None = None,
        model: str | None = None,
    ) -> None:
        """Store in all cache tiers.

        Args:
            prompt: Prompt
            response: Response to cache
            system: System prompt
            model: Model name
        """
        full_prompt = f"{system or ''}\n{prompt}\n{model or ''}"
        hash_key = hashlib.sha256(full_prompt.encode()).hexdigest()[:16]
        embedding = self._text_to_embedding(prompt)

        entry = CacheEntry(
            key=hash_key,
            prompt=prompt,
            response=response,
            embedding=embedding,
        )

        # Store in L1 (exact match)
        self._put_l1(hash_key, entry)

        # Store in L2 (semantic)
        self._put_l2(hash_key, entry)

        # Store in L3 (vault, async non-blocking)
        # TODO: Wire to vault asynchronously without awaiting
        # For MVP, skip

    def _put_l1(self, hash_key: str, entry: CacheEntry) -> None:
        """Add entry to L1 cache."""
        if len(self.l1_cache) >= self.max_l1_size and self.l1_insertion_order:
            # Evict oldest (FIFO)
            oldest_key = self.l1_insertion_order.pop(0)
            del self.l1_cache[oldest_key]

        self.l1_cache[hash_key] = entry
        self.l1_insertion_order.append(hash_key)

    def _put_l2(self, hash_key: str, entry: CacheEntry) -> None:
        """Add entry to L2 cache."""
        if len(self.l2_cache) >= self.max_l2_size:
            # Evict least frequently used
            if self.l2_lfu_counts:
                # Get minimum based on usage count
                get_fn = self.l2_lfu_counts.get
                lfu_key = min(self.l2_lfu_counts, key=get_fn)  # type: ignore
                del self.l2_cache[lfu_key]
                del self.l2_lfu_counts[lfu_key]

        self.l2_cache[hash_key] = entry
        self.l2_lfu_counts[hash_key] = 1

    def _promote_to_l1(self, hash_key: str, entry: CacheEntry) -> None:
        """Promote L2 hit to L1."""
        if hash_key not in self.l1_cache:
            self._put_l1(hash_key, entry)
            # Update LFU count
            if hash_key in self.l2_lfu_counts:
                self.l2_lfu_counts[hash_key] += 1

    async def _vault_lookup(self, prompt: str) -> str | None:
        """Search vault for similar executions."""
        # TODO: Wire to MCPClient
        # For now, return None
        return None

    async def _vault_store(self, prompt: str, response: str) -> None:
        """Persist to vault for L3 cache."""
        # TODO: Wire to MCPClient asynchronously
        # Non-blocking, so wrap in try/except
        try:
            pass  # TODO: implement
        except Exception as e:
            logger.debug(f"Vault store failed (non-critical): {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hit rates by tier and counts
        """
        total = self.hits_l1 + self.hits_l2 + self.hits_l3 + self.misses
        hit_rate = (
            (self.hits_l1 + self.hits_l2 + self.hits_l3) / total * 100
            if total > 0
            else 0.0
        )

        return {
            "l1_hits": self.hits_l1,
            "l2_hits": self.hits_l2,
            "l3_hits": self.hits_l3,
            "misses": self.misses,
            "total_requests": total,
            "overall_hit_rate": hit_rate,
            "l1_hit_rate": (
                self.hits_l1 / total * 100 if total > 0 else 0.0
            ),
            "l2_hit_rate": (
                self.hits_l2 / total * 100 if total > 0 else 0.0
            ),
            "l3_hit_rate": (
                self.hits_l3 / total * 100 if total > 0 else 0.0
            ),
            "l1_size": len(self.l1_cache),
            "l2_size": len(self.l2_cache),
            "similarity_threshold": self.similarity_threshold,
        }

    def clear(self) -> None:
        """Clear all cache tiers."""
        self.l1_cache.clear()
        self.l1_insertion_order.clear()
        self.l2_cache.clear()
        self.l2_lfu_counts.clear()
        self.hits_l1 = 0
        self.hits_l2 = 0
        self.hits_l3 = 0
        self.misses = 0
