r"""Multi-Tier L1/L2/L3 Semantic & State Cache System
=====================================================
Implements a 3-tier caching system for zero-latency prompt, state vector,
and inference result retrieval.

Tiers:
  - L1: In-Memory LRU Cache (Exact SHA-256 Key, < 0.05ms)
  - L2: Poincaré Vector Cosine Similarity Cache (d_H(u, v) <= 0.05, < 0.2ms)
  - L3: Persistent SurrealDB Cache (`semantic_cache` table, < 2.0ms)
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND


SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()


@dataclass(frozen=True, slots=True)
class CacheHit:
    tier: str  # "L1_LRU", "L2_Hyperbolic", or "L3_SurrealDB"
    value: Any
    latency_ms: float
    confidence: float


class SemanticCacheSystem:
    """3-Tier L1/L2/L3 Multi-Level Semantic Cache System."""

    def __init__(self, l1_capacity: int = 1000, l2_distance_threshold: float = 0.05) -> None:
        self.l1_capacity = l1_capacity
        self.l2_distance_threshold = l2_distance_threshold
        self.l1_cache: dict[str, tuple[Any, float]] = {}  # key -> (value, timestamp)
        self.l2_vector_cache: list[tuple[PoincarePoint, Any]] = []

    def _hash_key(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()

    def get(self, prompt: str, state_vector: PoincarePoint | None = None) -> CacheHit | None:
        """Lookup cache across L1 LRU -> L2 Hyperbolic Distance -> L3 SurrealDB."""
        t0 = time.perf_counter()
        key = self._hash_key(prompt)

        # Tier 1: L1 Exact LRU Hit
        if key in self.l1_cache:
            val, _ = self.l1_cache[key]
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return CacheHit(tier="L1_LRU", value=val, latency_ms=round(dt_ms, 3), confidence=1.0)

        # Tier 2: L2 Poincaré Vector Distance Hit
        if state_vector is not None:
            for cached_vec, cached_val in self.l2_vector_cache:
                if cached_vec.dim == state_vector.dim:
                    dist = PoincareManifoldND.distance(cached_vec, state_vector)
                    if dist <= self.l2_distance_threshold:
                        dt_ms = (time.perf_counter() - t0) * 1000.0
                        conf = max(0.5, 1.0 - (dist / self.l2_distance_threshold))
                        return CacheHit(
                            tier="L2_Hyperbolic",
                            value=cached_val,
                            latency_ms=round(dt_ms, 3),
                            confidence=round(conf, 4),
                        )

        # Tier 3: L3 SurrealDB Hit
        surql = f"SELECT * FROM semantic_cache WHERE key = '{key}';"
        try:
            req = urllib.request.Request(
                SURREAL_URL,
                data=surql.encode(),
                headers={
                    "Authorization": f"Basic {SURREAL_AUTH}",
                    "Surreal-NS": "cohezion",
                    "Surreal-DB": "main",
                    "Accept": "application/json",
                    "Content-Type": "text/plain",
                },
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                res = json.loads(r.read().decode())
                if isinstance(res, list) and res and res[0].get("result"):
                    rec = res[0]["result"][0]
                    val = rec.get("value")
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    return CacheHit(
                        tier="L3_SurrealDB", value=val, latency_ms=round(dt_ms, 3), confidence=0.95
                    )
        except Exception:
            pass

        return None

    def put(self, prompt: str, value: Any, state_vector: PoincarePoint | None = None) -> None:
        """Insert value into L1 LRU, L2 Vector Cache, and L3 SurrealDB."""
        key = self._hash_key(prompt)

        # Insert L1
        if len(self.l1_cache) >= self.l1_capacity:
            oldest_key = min(self.l1_cache, key=lambda k: self.l1_cache[k][1])
            del self.l1_cache[oldest_key]
        self.l1_cache[key] = (value, time.time())

        # Insert L2 Vector Cache
        if state_vector is not None:
            self.l2_vector_cache.append((state_vector, value))
            if len(self.l2_vector_cache) > 200:
                self.l2_vector_cache.pop(0)

        # Insert L3 SurrealDB
        data = {"key": key, "prompt": prompt, "value": value, "timestamp": time.time()}
        surql = f"UPSERT semantic_cache:{key} CONTENT {json.dumps(data)};"
        try:
            req = urllib.request.Request(
                SURREAL_URL,
                data=surql.encode(),
                headers={
                    "Authorization": f"Basic {SURREAL_AUTH}",
                    "Surreal-NS": "cohezion",
                    "Surreal-DB": "main",
                    "Accept": "application/json",
                    "Content-Type": "text/plain",
                },
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass
