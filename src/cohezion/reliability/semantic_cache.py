# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Semantic Caching Utility for Cohezion.
Uses vector similarity to retrieve cached agent responses.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.compound.exp_persistence.vault import get_vault_logger
from cohezion.core.persistence.redis_aggregator import get_redis


logger = logging.getLogger(__name__)


class SemanticCache:
    def __init__(self, cache_dir: str = "cache/semantic", threshold: float = 0.95):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold
        self.index_path = self.cache_dir / "index.json"
        self.vectors_path = self.cache_dir / "vectors.npy"

        self.vectors: list[np.ndarray] = []
        self.metadata: list[dict[str, Any]] = []
        self.redis = get_redis()
        self._vault = None
        self._load_cache()

    @property
    def vault(self):
        if self._vault is None:
            self._vault = get_vault_logger()
        return self._vault

    def _load_cache(self):
        """Load existing cache from disk if available."""
        if self.index_path.exists() and self.vectors_path.exists():
            try:
                self.metadata = json.loads(self.index_path.read_text())
                raw_vectors = np.load(self.vectors_path)
                self.vectors = list(raw_vectors)
            except Exception:
                # If loading fails, start fresh to avoid corruption
                self.metadata = []
                self.vectors = []

    def save(self):
        """Persist cache index and vectors to disk."""
        if not self.vectors:
            return

        try:
            self.index_path.write_text(json.dumps(self.metadata, indent=2))
            np.save(self.vectors_path, np.array(self.vectors))
        except Exception as e:
            logger.warning("Failed to persist semantic cache to disk: %s", e)

    async def search(
        self, query_vec: np.ndarray, query_text: str | None = None
    ) -> dict[str, Any] | None:
        """
        Perform semantic similarity search with Redis L1 tier.

        Args:
            query_vec: The vector representation of the query.
            query_text: The raw text of the query for exact-match L1 lookup.

        Returns:
            Optional[Dict[str, Any]]: The cached metadata if found.
        """
        # Tier 1: Redis Exact Match (L1) - Fastest for identical queries
        redis_key = ""
        if query_text:
            key_hash = hashlib.sha256(query_text.encode()).hexdigest()
            redis_key = f"semantic_cache:exact:{key_hash}"
            cached_result = await self.redis.get(redis_key)
            if cached_result:
                logger.debug(f"🔥 Redis L1 Hit for query hash: {key_hash[:8]}")
                return cached_result

        # Tier 2: Local Vector Search (L0) - High-speed memory search
        if not self.vectors:
            return None

        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return None

        matrix = np.array(self.vectors)
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0] = 1e-10

        cosine_sim = np.dot(matrix, query_vec) / (norms * q_norm)
        best_idx = np.argmax(cosine_sim)
        score = cosine_sim[best_idx]

        if score >= self.threshold:
            result = self.metadata[best_idx].copy()
            result["semantic_score"] = float(score)

            # Populate L1 cache for future exact hits
            if query_text:
                await self.redis.set(redis_key, result, ttl=3600 * 24)  # 24h TTL

            return result

        # Tier 3: Vault Search (L3) - Fallback for architectural patterns
        if query_text:
            try:
                guidance = self.vault.get_experience_guidance(query_text)
                if guidance and guidance.get("relevant_context"):
                    logger.debug(f"📜 Vault L3 Hit for query: {query_text[:20]}...")
                    return {
                        "response": (
                            f"VAULT GUIDANCE:\n{guidance.get('guidance', '')}\n\n"
                            f"CONTEXT:\n{json.dumps(guidance.get('relevant_context', []), indent=2)}"
                        ),
                        "semantic_score": 0.5,  # Qualitative hit
                        "source": "vault",
                    }
            except Exception as e:
                logger.debug(f"Vault L3 search failed: {e}")

        return None

    async def add(
        self,
        vector: np.ndarray,
        response: str,
        metadata: dict[str, Any],
        query_text: str | None = None,
    ):
        """Add a new entry to the semantic cache and broadcast to L1."""
        # Check if already exists locally
        for idx, m in enumerate(self.metadata):
            if m.get("response") == response:
                self.vectors[idx] = vector
                self.metadata[idx] = {
                    **m,
                    **metadata,
                    "timestamp": os.path.getmtime(self.index_path)
                    if self.index_path.exists()
                    else 0,
                }
                return

        self.vectors.append(vector)
        self.metadata.append({"response": response, "timestamp": 0, **metadata})
        self.save()

        # Broadcast to L1 if query text is provided
        if query_text:
            key_hash = hashlib.sha256(query_text.encode()).hexdigest()
            redis_key = f"semantic_cache:exact:{key_hash}"
            await self.redis.set(
                redis_key,
                {
                    **metadata,
                    "response": response,
                    "semantic_score": 1.0,  # Exact match
                },
                ttl=3600 * 24,
            )

    def get_stats(self) -> dict[str, Any]:
        """Return cache health and size metrics."""
        return {
            "size": len(self.vectors),
            "threshold": self.threshold,
            "dimension": self.vectors[0].shape[0] if self.vectors else 0,
        }
