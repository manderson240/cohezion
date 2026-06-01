"""Multi-tier semantic cache for LLM inference.

Architecture:
    L1: Exact hash matching (FIFO, 512 entries)
    L2: Semantic similarity (cosine >0.58/0.80, LFU, 1024 entries)
    L3: Vault lookup (async, non-blocking)

Embeddings: nomic-embed-text-v2-moe-GGUF (768D, lemonade) primary on XDNA2;
            sentence-transformers all-MiniLM-L6-v2 (384D) on other systems; FLUME VAE fallback.
Target: 100% near-duplicate hit rate, 0% novel-prompt false positives (exp_OOOO2).
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cohezion.cache.lemonade_encoder import OPTIMAL_THRESHOLD as _LEMONADE_THRESHOLD
from cohezion.cache.lemonade_encoder import get_lemonade_encoder
from cohezion.cache.text_encoder import get_text_encoder
from cohezion.flume.vae_encoder import get_encoder


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


_singleton: "SemanticCache | None" = None


class SemanticCache:
    """Multi-tier cache with semantic similarity matching.

    Tiers:
        L1: Exact hash (SHA-256, FIFO, 512 entries)
        L2: Semantic similarity (cosine > threshold, LFU, 1024 entries)
        L3: Vault lookup (async, non-blocking)

    Parameters
    ----------
    similarity_threshold : float
        Cosine similarity threshold for L2 hits (default: 0.75, empirically optimal)
    max_l1_size : int
        Maximum L1 cache entries (default: 512)
    max_l2_size : int
        Maximum L2 cache entries (default: 1024)
    mcp_client : MCPClient | None
        Optional MCPClient for L3 vault lookups (default: None = disabled)
    """

    # Default thresholds per encoder dimension (exp_RRRR + exp_OOOO2, 2026-05-29)
    # nomic-embed 768D: 0.58 (exp_OOOO2 — 0% FP, 100% near-dup hits; primary on XDNA2)
    # sentence-transformers 384D: 0.80 (exp_BBBB — 0% FP, 87% near-dup hits)
    # FLUME VAE 256D: 0.45 (exp_RRRR — 0% FP, 88% paraphrase hits; XDNA2 fallback)
    _THRESHOLD_BY_DIM: dict = {768: _LEMONADE_THRESHOLD, 384: 0.80, 256: 0.45}
    _DEFAULT_THRESHOLD = 0.80

    def _load_profile_threshold(self) -> float | None:
        """Load calibrated threshold from config/calibration_profiles.json if present.

        Bypasses loading if running under pytest to ensure test isolation.
        """
        import os

        if (
            "PYTEST_CURRENT_TEST" in os.environ
            or "COHEZION_IGNORE_CALIBRATION_PROFILE" in os.environ
        ):
            return None

        try:
            from pathlib import Path

            from cohezion.config.unified import get_config

            root_dir = Path(get_config().root_dir)
            profile_path = root_dir / "config" / "calibration_profiles.json"
            if profile_path.exists():
                with open(profile_path, encoding="utf-8") as f:
                    data = json.load(f)
                    val = (
                        data.get("semantic_cache", {})
                        .get("parameters", {})
                        .get("similarity_threshold")
                    )
                    if isinstance(val, (int, float)) and 0.0 <= val <= 1.0:
                        logger.info(
                            "SemanticCache: Loaded calibrated threshold = %s from profile", val
                        )
                        return float(val)
        except Exception as e:
            logger.debug("SemanticCache: Failed to load profile: %s", e)
        return None

    def __init__(
        self,
        similarity_threshold: float = 0.80,  # exp_BBBB: 0.80 for sentence-transformers; auto-tuned to 0.45 for FLUME VAE (exp_RRRR)
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
        self.max_l1_size = max_l1_size
        self.max_l2_size = max_l2_size
        self.mcp_client = mcp_client
        self.enable_adaptive_threshold = enable_adaptive_threshold

        # Auto-tune threshold for the active encoder (exp_RRRR, 2026-05-29)
        # When using the default (0.80), probe the actual encoder dimension and adjust.
        # sentence-transformers crashes on XDNA2, falling back to FLUME VAE 256D;
        # FLUME VAE similarity scores are lower (0.40-0.65 range vs 0.80-0.97).
        profile_threshold = self._load_profile_threshold()
        if profile_threshold is not None:
            similarity_threshold = profile_threshold
        elif similarity_threshold == self._DEFAULT_THRESHOLD:
            similarity_threshold = self._auto_tune_threshold_for_encoder()
        self.similarity_threshold = similarity_threshold
        self.initial_threshold = similarity_threshold

        # Register as singleton only when using auto-tuned default (not test-overridden)
        global _singleton
        if _singleton is None and similarity_threshold in self._THRESHOLD_BY_DIM.values():
            _singleton = self

        # L1 cache: exact hash matches
        self.l1_cache: dict[str, CacheEntry] = {}
        self.l1_insertion_order: list[str] = []

        # L2 cache: semantic matches
        self.l2_cache: dict[str, CacheEntry] = {}
        self.l2_lfu_counts: dict[str, int] = {}

        # Vectorized L2 scan: pre-stacked embedding matrix for BLAS dot
        self._l2_keys: list[str] = []
        self._l2_matrix: np.ndarray | None = None  # shape (n, 384)

        # Stats
        self.hits_l1 = 0
        self.hits_l2 = 0
        self.hits_l3 = 0
        self.misses = 0

        # Adaptive threshold tracking
        self._threshold_adjustment_interval = 100  # Adjust every 100 ops
        self._background_tasks: set[asyncio.Task] = set()

    @staticmethod
    def _auto_tune_threshold_for_encoder() -> float:
        """Probe the embedding encoder and return the appropriate threshold.

        Calibrated thresholds per encoder (exp_RRRR + exp_OOOO2, 2026-05-29):
          768D → 0.58 (nomic-embed via lemonade, 0% FP, 100% near-dup hits — exp_OOOO2)
          384D → 0.80 (sentence-transformers, 0% FP, 87% near-dup hits — exp_BBBB)
          256D → 0.45 (FLUME VAE, 0% FP, 88% paraphrase hits — exp_RRRR)
        """
        try:
            probe = SemanticCache._text_to_embedding("routing task probe")
            dim = probe.shape[0]
            threshold = SemanticCache._THRESHOLD_BY_DIM.get(dim, SemanticCache._DEFAULT_THRESHOLD)
            if threshold != SemanticCache._DEFAULT_THRESHOLD:
                logger.debug("Encoder detected: %dD → threshold %.2f", dim, threshold)
            return threshold
        except Exception:
            return SemanticCache._DEFAULT_THRESHOLD

    @classmethod
    def get_instance(cls) -> "SemanticCache":
        """Return the module-level singleton, creating it on first call.

        Called by template_matcher.try_template_match() to activate cache
        in the CompoundExecutor pipeline without requiring explicit wiring.
        The singleton uses default parameters (threshold=0.80, exp_BBBB optimal).
        """
        global _singleton
        if _singleton is None:
            _singleton = cls()
        return _singleton

    @staticmethod
    def _text_to_embedding(text: str) -> np.ndarray:
        """Convert text to production semantic embedding.

        Priority chain on XDNA2 (exp_OOOO2, 2026-05-29):
          1. nomic-embed-text-v2-moe-GGUF (768D, lemonade 13305) — primary
          2. sentence-transformers all-MiniLM-L6-v2 (384D) — non-XDNA2
          3. FLUME VAE (256D) — fallback when checkpoint available
          4. SHA-256 hash (384D) — absolute last resort, no semantic discrimination

        Returns:
            numpy array (dim varies by encoder), L2-normalized
        """
        # 1. Lemonade nomic-embed (primary on XDNA2 — sentence-transformers crashes there)
        try:
            enc = get_lemonade_encoder()
            if enc.is_available():
                return enc.encode(text)
        except Exception as e:
            logger.debug("Lemonade encoder failed: %s", e)

        # 2. sentence-transformers (primary on non-XDNA2 systems)
        try:
            encoder = get_text_encoder()
            return encoder.encode(text)
        except Exception as e:
            logger.debug("Semantic encoding failed: %s", e)

        # 3. FLUME VAE fallback
        try:
            vae_encoder = get_encoder()
            return vae_encoder.encode(text)
        except Exception as vae_e:
            logger.debug("VAE encoding also failed: %s — using hash fallback", vae_e)

        # 4. SHA-256 hash — no semantic discrimination, last resort
        hash_bytes = hashlib.sha256(text.encode()).digest()
        embedding = np.zeros(384, dtype=np.float32)
        for i in range(384):
            embedding[i] = hash_bytes[i % len(hash_bytes)] / 255.0
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
            # Too many misses - relax threshold (floor = 85% of initial, encoder-aware)
            new_threshold = max(self.initial_threshold * 0.85, self.initial_threshold - 0.05)
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
        hash_key = hashlib.sha256(full_prompt.encode()).hexdigest()[:16]

        # L1: Exact match
        if hash_key in self.l1_cache:
            entry = self.l1_cache[hash_key]
            self.hits_l1 += 1
            return entry.response

        # L2: Vectorized semantic similarity via pre-stacked BLAS dot
        query_embedding = self._text_to_embedding(prompt)
        best_match = None
        best_similarity = 0.0
        current_threshold = self._get_adaptive_threshold()

        if self._l2_matrix is not None and len(self._l2_keys) > 0:
            sims = np.dot(self._l2_matrix, query_embedding)
            best_idx = int(np.argmax(sims))
            best_similarity = float(sims[best_idx])
            best_key = self._l2_keys[best_idx]
            best_match = self.l2_cache.get(best_key)

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

        # Store in L3 (vault, async non-blocking fire-and-forget)
        # Schedule vault storage without awaiting (non-blocking pattern)
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
            oldest_key = self.l1_insertion_order.pop(0)
            del self.l1_cache[oldest_key]

        self.l1_cache[hash_key] = entry
        self.l1_insertion_order.append(hash_key)

    def _put_l2(self, hash_key: str, entry: CacheEntry) -> None:
        """Add entry to L2 cache, maintaining the vectorized embedding matrix."""
        if self.max_l2_size <= 0:
            return

        if len(self.l2_cache) >= self.max_l2_size and self.l2_lfu_counts:
            get_fn = self.l2_lfu_counts.get
            lfu_key = min(self.l2_lfu_counts, key=get_fn)  # type: ignore
            del self.l2_cache[lfu_key]
            del self.l2_lfu_counts[lfu_key]
            # Rebuild matrix after eviction (infrequent — only when L2 is full)
            self._l2_keys = list(self.l2_cache.keys())
            if self._l2_keys:
                self._l2_matrix = np.stack([self.l2_cache[k].embedding for k in self._l2_keys])
            else:
                self._l2_matrix = None

        self.l2_cache[hash_key] = entry
        self.l2_lfu_counts[hash_key] = 1

        # Incremental append to matrix (cheap path — no eviction)
        self._l2_keys.append(hash_key)
        row = entry.embedding.reshape(1, -1)
        self._l2_matrix = (
            np.vstack([self._l2_matrix, row]) if self._l2_matrix is not None else row.copy()
        )

    def _promote_to_l1(self, hash_key: str, entry: CacheEntry) -> None:
        """Promote L2 hit to L1."""
        if hash_key not in self.l1_cache:
            self._put_l1(hash_key, entry)
            # Update LFU count
            if hash_key in self.l2_lfu_counts:
                self.l2_lfu_counts[hash_key] += 1

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
        self._l2_keys.clear()
        self._l2_matrix = None
        self.hits_l1 = 0
        self.hits_l2 = 0
        self.hits_l3 = 0
        self.misses = 0
