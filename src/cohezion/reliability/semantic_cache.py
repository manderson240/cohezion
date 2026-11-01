# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Semantic Caching Utility for Cohezion.
Uses vector similarity to retrieve cached agent responses.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.compound.exp_persistence.vault import get_vault_logger
from cohezion.core.persistence.redis_aggregator import get_redis
from cohezion.flume.canonical_latent import LATENT_DIM


logger = logging.getLogger(__name__)


def query_digest(query_text: str) -> str:
    """Digest of the FULL query text (stored prompts are truncated, so they cannot identify it)."""
    return hashlib.sha256(query_text.encode()).hexdigest()


class SemanticCache:
    """Scoped answer cache: an entry is only ever served inside the scope that stored it.

    ``scope`` is an opaque string (BaseAgent: agent class + model + system prompt). An entry or a
    lookup without a scope is never served, so legacy unscoped entries on disk or in Redis can
    not leak into a scoped lookup.

    ``exact_only`` (default True) additionally requires the stored query text to be identical to
    the lookup text. This is a deliberate precision choice, not a performance one: on the
    canonical MiniLM-256 latent no cosine threshold separates a paraphrase from a
    direction-reversed instruction ("Move $100 from savings to checking" vs its reverse = 0.993).
    A scope fix cannot repair that embedding limit; only not serving fuzzy matches can. With
    ``exact_only=False`` the cosine threshold decides and wrong answers CAN be served.

    ``ttl_seconds`` (None = unbounded) bounds every tier: an entry older than that, or one with no
    timestamp (written by an earlier version), is never served from Redis or the local vectors.
    """

    # Redis key version: v1 keys were unscoped (sha256 of the query only) and are never read.
    _REDIS_PREFIX = "semantic_cache:exact:v2:"

    def __init__(
        self,
        cache_dir: str = "cache/semantic",
        threshold: float = 0.95,
        exact_only: bool = True,
        ttl_seconds: float | None = None,
    ):
        self.exact_only = exact_only
        self.ttl_seconds = ttl_seconds
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

    def _purge_stale_widths(self) -> int:
        """Drop (vector, metadata) pairs whose vector is not LATENT_DIM wide, in lockstep.

        Entries written by an older producer (hash 256-d is the same width but a different space
        and cannot be told apart here; 384/768-d can) would make ``np.array(self.vectors)`` ragged
        and silently lose every later save. Returns the number of pairs dropped.
        """
        n = min(len(self.vectors), len(self.metadata))
        keep = [i for i in range(n) if self.vectors[i].shape == (LATENT_DIM,)]
        dropped = len(self.vectors) - len(keep)
        if dropped or len(self.metadata) != len(keep):
            self.vectors = [self.vectors[i] for i in keep]
            self.metadata = [self.metadata[i] for i in keep]
        return dropped

    def _load_cache(self):
        """Load existing cache from disk if available."""
        if self.index_path.exists() and self.vectors_path.exists():
            try:
                self.metadata = json.loads(self.index_path.read_text())
                raw_vectors = np.load(self.vectors_path)
                self.vectors = [np.asarray(v) for v in raw_vectors]
            except Exception:
                # If loading fails, start fresh to avoid corruption
                self.metadata = []
                self.vectors = []
                return
            dropped = self._purge_stale_widths()
            if dropped:
                logger.warning(
                    "semantic cache: dropped %d persisted entries not %d-d (older producer)",
                    dropped,
                    LATENT_DIM,
                )
                self.save()

    def save(self):
        """Persist cache index and vectors to disk (stale widths purged first, lockstep)."""
        self._purge_stale_widths()
        if not self.vectors and not self.vectors_path.exists():
            return

        try:
            matrix = (
                np.stack(self.vectors)
                if self.vectors
                else np.empty((0, LATENT_DIM), dtype=np.float32)
            )
            self.index_path.write_text(json.dumps(self.metadata, indent=2))
            np.save(self.vectors_path, matrix)
        except Exception as e:
            logger.warning("Failed to persist semantic cache to disk: %s", e)

    def _redis_key(self, scope: str, query_text: str) -> str:
        return self._REDIS_PREFIX + hashlib.sha256(f"{scope}\0{query_text}".encode()).hexdigest()

    def _expired(self, meta: dict[str, Any]) -> bool:
        """True when the entry is older than ``ttl_seconds``. No/zero/invalid timestamp = expired."""
        if self.ttl_seconds is None:
            return False
        stamp = meta.get("timestamp")
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or stamp <= 0:
            return True
        return time.time() - stamp >= self.ttl_seconds

    def _redis_ttl(self) -> float:
        return min(3600 * 24, self.ttl_seconds) if self.ttl_seconds is not None else 3600 * 24

    def _in_scope(
        self, meta: dict[str, Any], scope: str, qdigest: str | None, exact_only: bool
    ) -> bool:
        if meta.get("scope") != scope:  # missing scope never matches
            return False
        if self._expired(meta):
            return False
        return not exact_only or (qdigest is not None and meta.get("query_digest") == qdigest)

    async def search(
        self,
        query_vec: np.ndarray,
        query_text: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Perform a scoped lookup: Redis L1, then local vectors (then vault, fuzzy mode only).

        Args:
            query_vec: The vector representation of the query.
            query_text: The raw text of the query (L1 key and, in exact mode, the identity check).
            scope: Required. ``None`` is refused (returns None) rather than treated as a wildcard.

        Returns:
            Optional[Dict[str, Any]]: The cached metadata if found.
        """
        if scope is None:
            return None
        qdigest = query_digest(query_text) if query_text else None

        # Tier 1: Redis Exact Match (L1) - keyed by scope AND full query text
        redis_key = ""
        if query_text:
            redis_key = self._redis_key(scope, query_text)
            cached_result = await self.redis.get(redis_key)
            if (
                isinstance(cached_result, dict)
                and cached_result.get("scope") == scope
                and cached_result.get("query_digest") == qdigest
                and not self._expired(cached_result)
            ):
                logger.debug("Redis L1 hit for %s", redis_key[-8:])
                return cached_result

        # Tier 2: Local Vector Search (L0) - High-speed memory search.
        # Only vectors of the query's width are comparable; entries persisted by an older
        # producer (different width) are ignored, never compared and never a crash.
        usable = [
            i
            for i, v in enumerate(self.vectors)
            if v.shape == query_vec.shape
            and i < len(self.metadata)
            and self._in_scope(self.metadata[i], scope, qdigest, self.exact_only)
        ]
        if not usable:
            return None if self.exact_only else await self._vault_hit(query_text)

        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return None

        matrix = np.array([self.vectors[i] for i in usable])
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0] = 1e-10

        cosine_sim = np.dot(matrix, query_vec) / (norms * q_norm)
        best_local = int(np.argmax(cosine_sim))
        best_idx = usable[best_local]
        score = cosine_sim[best_local]

        if score >= self.threshold:
            result = self.metadata[best_idx].copy()
            result["semantic_score"] = float(score)

            # Populate L1 cache for future exact hits
            if query_text:
                await self.redis.set(
                    redis_key, {**result, "query_digest": qdigest}, ttl=self._redis_ttl()
                )

            return result

        return None if self.exact_only else await self._vault_hit(query_text)

    async def _vault_hit(self, query_text: str | None) -> dict[str, Any] | None:
        """Tier 3 (vault guidance). Unscoped by nature and not an answer to THIS prompt, so it is
        reachable only in fuzzy mode; exact mode fails closed."""
        if not query_text:
            return None
        try:
            guidance = self.vault.get_experience_guidance(query_text)
            if guidance and guidance.get("relevant_context"):
                logger.debug("Vault L3 hit for query: %s...", query_text[:20])
                return {
                    "response": f"VAULT GUIDANCE:\n{guidance.get('guidance', '')}\n\nCONTEXT:\n{json.dumps(guidance.get('relevant_context', []), indent=2)}",
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
        scope: str | None = None,
    ):
        """Add a new entry to the semantic cache and broadcast to L1.

        An entry stored without ``scope`` is persisted but can never be served.
        """
        if vector.shape != (LATENT_DIM,):
            logger.warning(
                "semantic cache add skipped: vector shape %s is not (%d,)", vector.shape, LATENT_DIM
            )
            return
        qdigest = query_digest(query_text) if query_text else None
        metadata = {**metadata, "scope": scope, "query_digest": qdigest}
        # Check if already exists locally: same scope, same query, same response
        for idx, m in enumerate(self.metadata):
            if (
                m.get("response") == response
                and m.get("scope") == scope
                and m.get("query_digest") == qdigest
            ):
                self.vectors[idx] = vector
                self.metadata[idx] = {
                    **m,
                    **metadata,
                    "timestamp": time.time(),
                }
                self.save()
                return

        self.vectors.append(vector)
        stamped = {**metadata, "timestamp": time.time()}
        self.metadata.append({"response": response, **stamped})
        self.save()

        # Broadcast to L1 only for a scoped entry
        if query_text and scope is not None:
            await self.redis.set(
                self._redis_key(scope, query_text),
                {
                    **stamped,
                    "response": response,
                    "semantic_score": 1.0,  # Exact match
                },
                ttl=self._redis_ttl(),
            )

    def get_stats(self) -> dict[str, Any]:
        """Return cache health and size metrics."""
        return {
            "size": len(self.vectors),
            "threshold": self.threshold,
            "dimension": self.vectors[0].shape[0] if self.vectors else 0,
        }
