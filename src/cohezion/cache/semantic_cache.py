"""Multi-tier semantic cache for LLM inference.

Architecture:
    L1: Exact hash matching (FIFO, 512 entries)
    L2: Semantic similarity (cosine >0.92, LFU, 1024 entries)
    L3: Vault lookup (async, non-blocking)

Embeddings: FLUME VAE encoder (256D) for real semantic similarity
Target: 70%+ cache hit rate with sub-100ms lookup latency.
"""

import asyncio
import hashlib
import json
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from cohezion.cache.text_encoder import get_text_encoder
from cohezion.flume.vae_encoder import get_encoder


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CacheEntry:
    """Single cache entry."""

    key: str
    prompt: str
    response: str
    embedding: np.ndarray


class SemanticCache:
    """Multi-tier cache with semantic similarity matching.

    Tiers:
        L1: Exact hash (SHA-256, FIFO, 512 entries)
        L2: Semantic similarity (cosine > threshold, LFU, 1024 entries)
        L3: Vault lookup (async, non-blocking)

    Parameters
    ----------
    similarity_threshold : float
        Cosine similarity threshold for L2 hits (default: 0.88)
    max_l1_size : int
        Maximum L1 cache entries (default: 512)
    max_l2_size : int
        Maximum L2 cache entries (default: 1024)
    mcp_client : MCPClient | None
        Optional MCPClient for L3 vault lookups (default: None = disabled)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.88,
        max_l1_size: int = 512,
        max_l2_size: int = 1024,
        mcp_client: Any = None,
        enable_adaptive_threshold: bool = True,
    ):
        """Initialize semantic cache.

        Args:
            similarity_threshold: Cosine similarity threshold for L2
            max_l1_size: L1 cache size
            max_l2_size: L2 cache size
            mcp_client: Optional MCPClient for L3 vault operations
            enable_adaptive_threshold: Enable adaptive threshold tuning (default: True)
        """
        self.similarity_threshold = similarity_threshold
        self.initial_threshold = similarity_threshold
        self.max_l1_size = max_l1_size
        self.max_l2_size = max_l2_size
        self.mcp_client = mcp_client
        self.enable_adaptive_threshold = enable_adaptive_threshold

        # L1 cache: exact hash matches
        self.l1_cache: dict[str, CacheEntry] = {}
        self.l1_insertion_order: deque[str] = deque()

        # L2 cache: semantic matches
        self.l2_cache: dict[str, CacheEntry] = {}
        self.l2_lfu_counts: dict[
            str, int
        ] = {}  # unused since FIFO ring buffer (kept for API compat)

        # Pre-allocated ring-buffer matrix for O(1) L2 inserts (eliminates np.vstack)
        self._l2_matrix = np.zeros((max_l2_size, 384), dtype=np.float32)
        self._l2_keys: list[str] = [""] * max_l2_size  # slot → key, '' = unused
        self._l2_write_idx = 0  # next ring-buffer slot to write

        # Stats
        self.hits_l1 = 0
        self.hits_l2 = 0
        self.hits_l3 = 0
        self.misses = 0

        # Memoized SHA-256 key cache: full_prompt -> hash_key
        # Avoids recomputing SHA-256 for repeated prompts (hot path optimization)
        self._hash_cache: dict[str, str] = {}

        # Adaptive threshold tracking
        self._threshold_adjustment_interval = 100  # Adjust every 100 ops
        self._background_tasks: set[asyncio.Task] = set()

    @staticmethod
    def _text_to_embedding(text: str) -> np.ndarray:
        """Convert text to production semantic embedding.

        Uses semantic text encoder (sentence-transformers) for native 384D
        semantic embeddings with proper semantic discrimination.

        Args:
            text: Text to embed

        Returns:
            384D numpy array, normalized for cosine similarity
        """
        try:
            # Use semantic encoder (all-MiniLM-L6-v2 native 384D)
            encoder = get_text_encoder()
            return encoder.encode(text)
        except Exception as e:
            logger.debug(f"Semantic encoding failed: {e}")
            # Fallback to FLUME VAE if available
            try:
                vae_encoder = get_encoder()
                return vae_encoder.encode(text)
            except Exception as vae_e:
                logger.debug(f"VAE encoding also failed: {vae_e}, using hash fallback")
                # Final fallback to deterministic hash
                hash_obj = hashlib.sha256(text.encode())
                hash_bytes = hash_obj.digest()

                embedding = np.zeros(384, dtype=np.float32)
                for i in range(384):
                    byte_idx = i % len(hash_bytes)
                    embedding[i] = hash_bytes[byte_idx] / 255.0

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

    def _get_adaptive_threshold(self) -> float:
        """Adjust similarity threshold based on observed hit rates.

        Adaptive tuning ensures optimal L2 cache hit rate:
        - If hit rate <5%: Decrease threshold (more permissive, ~0.87)
        - If hit rate >40%: Increase threshold (more precise, ~0.97)
        - Otherwise: Keep stable at initial value

        Returns:
            Adjusted cosine similarity threshold
        """
        if not self.enable_adaptive_threshold:
            return self.similarity_threshold

        total_ops = self.hits_l1 + self.hits_l2 + self.hits_l3 + self.misses
        if total_ops < self._threshold_adjustment_interval:
            # Need minimum data before adjustment
            return self.similarity_threshold

        l2_hit_rate = self.hits_l2 / total_ops if total_ops > 0 else 0

        if l2_hit_rate < 0.05:
            # Too many misses - relax threshold
            new_threshold = max(0.70, self.initial_threshold - 0.05)
            logger.debug(
                f"L2 hit rate {l2_hit_rate:.1%} too low, "
                f"relaxing threshold: {self.similarity_threshold:.2f} → {new_threshold:.2f}"
            )
            return new_threshold
        if l2_hit_rate > 0.40:
            # Too many hits - tighten threshold for precision
            new_threshold = min(0.97, self.initial_threshold + 0.05)
            logger.debug(
                f"L2 hit rate {l2_hit_rate:.1%} too high, "
                f"tightening threshold: {self.similarity_threshold:.2f} → {new_threshold:.2f}"
            )
            return new_threshold
        # Hit rate in target range (5-40%)
        return self.similarity_threshold

    async def get(
        self, prompt: str, system: str | None = None, model: str | None = None
    ) -> str | None:
        """Lookup with 3-tier fallback.

        Checks L1 (exact), L2 (semantic), then L3 (vault).
        Promotes hits to faster tiers. Uses adaptive threshold tuning.

        Args:
            prompt: Prompt to lookup
            system: System prompt (included in cache key)
            model: Model name (included in cache key)

        Returns:
            Cached response or None if miss
        """
        full_prompt = f"{system or ''}\n{prompt}\n{model or ''}"
        hash_key = self._hash_cache.get(full_prompt) or self._hash_cache.setdefault(
            full_prompt, hashlib.sha256(full_prompt.encode()).hexdigest()[:16]
        )

        # L1: Exact match
        if hash_key in self.l1_cache:
            entry = self.l1_cache[hash_key]
            self.hits_l1 += 1
            return entry.response

        # L2 fast path: exact hash hit (entry was evicted from L1 but still in L2)
        # This avoids the O(n) similarity scan for repeat prompts. Identical prompt
        # → identical hash → guaranteed cosine similarity = 1.0, so a hash match
        # always passes any reasonable threshold.
        l2_exact = self.l2_cache.get(hash_key)
        if l2_exact is not None:
            self.hits_l2 += 1
            return l2_exact.response

        # L2: Vectorized semantic similarity via pre-stacked BLAS dot
        query_embedding = self._text_to_embedding(prompt)
        best_match = None
        best_similarity = 0.0
        current_threshold = self._get_adaptive_threshold()

        if self.l2_cache:
            sims = np.dot(self._l2_matrix, query_embedding)
            best_idx = int(np.argmax(sims))
            best_key = self._l2_keys[best_idx]
            best_similarity = float(sims[best_idx]) if best_key else 0.0
            best_match = self.l2_cache.get(best_key) if best_key else None

        if best_match and best_similarity > current_threshold:
            self.hits_l2 += 1
            # Promote to L1
            self._promote_to_l1(hash_key, best_match)
            return best_match.response

        # L3: Vault lookup (async, non-blocking)
        vault_result = await self._vault_lookup(prompt)
        if vault_result:
            self.hits_l3 += 1
            # Create entry and promote to L1
            embedding = self._text_to_embedding(prompt)
            entry = CacheEntry(
                key=hash_key,
                prompt=prompt,
                response=vault_result,
                embedding=embedding,
            )
            self._promote_to_l1(hash_key, entry)
            return vault_result

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
        hash_key = self._hash_cache.get(full_prompt) or self._hash_cache.setdefault(
            full_prompt, hashlib.sha256(full_prompt.encode()).hexdigest()[:16]
        )
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

        # Store in L3 only when vault client is configured (skip task creation overhead otherwise)
        if self.mcp_client:
            try:
                _task = asyncio.create_task(self._vault_store(prompt, response))
                self._background_tasks.add(_task)
                _task.add_done_callback(self._background_tasks.discard)
            except RuntimeError:
                # No event loop running (e.g., sync context) - skip L3 storage
                logger.debug("No event loop for L3 vault store (non-critical)")

    def _put_l1(self, hash_key: str, entry: CacheEntry) -> None:
        """Add entry to L1 cache."""
        if len(self.l1_cache) >= self.max_l1_size and self.l1_insertion_order:
            # Evict oldest (FIFO)
            oldest_key = self.l1_insertion_order.popleft()
            del self.l1_cache[oldest_key]

        self.l1_cache[hash_key] = entry
        self.l1_insertion_order.append(hash_key)

    def _put_l2(self, hash_key: str, entry: CacheEntry) -> None:
        """Add entry to L2 cache using a pre-allocated ring buffer — O(1) insert."""
        if self.max_l2_size <= 0:
            return

        slot = self._l2_write_idx
        # Evict the entry at this slot (FIFO — oldest entry goes first)
        old_key = self._l2_keys[slot]
        if old_key and old_key in self.l2_cache:
            del self.l2_cache[old_key]

        # Write directly to pre-allocated slot — no allocation, no copy
        self._l2_matrix[slot] = entry.embedding
        self._l2_keys[slot] = hash_key
        self.l2_cache[hash_key] = entry
        self._l2_write_idx = (slot + 1) % self.max_l2_size

    def _promote_to_l1(self, hash_key: str, entry: CacheEntry) -> None:
        """Promote L2 hit to L1."""
        if hash_key not in self.l1_cache:
            self._put_l1(hash_key, entry)

    async def _vault_lookup(self, prompt: str) -> str | None:
        """Search vault for similar execution patterns.

        Uses MCPClient to search for prompts with similar responses
        from prior successful executions. Non-blocking on failure.

        Args:
            prompt: Prompt to search for

        Returns:
            Cached response if found, None otherwise
        """
        if not self.mcp_client:
            return None

        try:
            # Search vault for cache patterns matching this prompt
            # Look for prompts that were successfully cached before
            search_query = f"{prompt[:50]} cache pattern"

            # Run synchronous vault_search in default executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self.mcp_client.vault_search, search_query)

            if not results:
                return None

            # Extract response from top result
            # Cache pattern files store prompt + response as JSON
            if results and len(results) > 0:
                first_result = results[0]
                if isinstance(first_result, dict):
                    # Try to read the cache pattern file
                    path = first_result.get("path", "")
                    if path:
                        try:
                            content = await loop.run_in_executor(
                                None, self.mcp_client.vault_read, path
                            )
                            # Parse as JSON cache entry
                            cache_data = json.loads(content)
                            response = cache_data.get("response", "")
                            if response and len(response) > 20:
                                logger.debug(f"L3 vault hit for prompt from {path}")
                                return response

                        except (json.JSONDecodeError, FileNotFoundError) as e:
                            logger.debug(f"Cache pattern parse failed: {e}")
                            # Fall through to return None

            return None

        except Exception as e:
            # Non-blocking: log and return None (NON_CRITICAL_TRACKING_PATTERN)
            logger.debug(f"Vault lookup failed (non-critical): {e}")
            return None

    async def _vault_store(self, prompt: str, response: str) -> None:
        """Persist successful prompt-response pair to vault.

        Stores to vault for future L3 cache lookups. Non-blocking
        on failure - vault persistence is nice-to-have, never essential.

        Args:
            prompt: Prompt that was cached
            response: Response that was cached
        """
        if not self.mcp_client:
            return

        try:
            # Store as a cache entry pattern in vault
            # This allows future sessions to find and reuse it
            timestamp = time.time()
            cache_entry = {
                "prompt": prompt[:200],  # Truncate for readability
                "response": response[:500],  # Truncate response
                "timestamp": timestamp,
            }

            # Create a cache pattern note in vault
            # Use timestamp + hash to avoid collisions
            # Security: SHA-256 used for non-security identifier (cache entry ID)
            entry_hash = hashlib.sha256(f"{prompt}{timestamp}".encode()).hexdigest()[:8]
            vault_path = f"cache_patterns/cache_entry_{entry_hash}.json"

            # Run synchronous vault_write in executor (non-blocking)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.mcp_client.vault_write,
                vault_path,
                json.dumps(cache_entry, indent=2),
            )
            logger.debug(f"L3 vault stored: {vault_path}")

        except Exception as e:
            # Non-blocking: log and continue (NON_CRITICAL_TRACKING_PATTERN)
            logger.debug(f"Vault store failed (non-critical): {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hit rates by tier and counts
        """
        total = self.hits_l1 + self.hits_l2 + self.hits_l3 + self.misses
        hit_rate = (self.hits_l1 + self.hits_l2 + self.hits_l3) / total * 100 if total > 0 else 0.0

        return {
            "l1_hits": self.hits_l1,
            "l2_hits": self.hits_l2,
            "l3_hits": self.hits_l3,
            "misses": self.misses,
            "total_requests": total,
            "overall_hit_rate": hit_rate,
            "l1_hit_rate": (self.hits_l1 / total * 100 if total > 0 else 0.0),
            "l2_hit_rate": (self.hits_l2 / total * 100 if total > 0 else 0.0),
            "l3_hit_rate": (self.hits_l3 / total * 100 if total > 0 else 0.0),
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
        self._l2_keys = [""] * self.max_l2_size
        self._l2_matrix[:] = 0.0
        self._l2_write_idx = 0
        self.hits_l1 = 0
        self.hits_l2 = 0
        self.hits_l3 = 0
        self.misses = 0
