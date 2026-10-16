"""Token-Efficient Semantic Cache & Request Batching System.
===========================================================
Implements token optimization strategies:
1. Tier 0 Deterministic Bypass: Zero-cost AutoHarness AST policy checks evaluate in 0 ms and 0 tokens.
2. SHA-256 Semantic Caching: Dual-layer (Memory LRU + On-Disk) with TTL and hit/miss telemetry in `cache/semantic/`.
3. Micro-Batching Engine: Aggregates concurrent evaluation or inference queries into batches to minimize API overhead.
"""

from __future__ import annotations

import collections
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("semantic_batch_cache")

WORKSPACE = Path(
    "/home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push"
)
CACHE_DIR = WORKSPACE / "cache" / "semantic"


@dataclass(slots=True)
class CacheTelemetry:
    """Telemetry tracking token savings and hit rates."""

    cache_hits: int = 0
    cache_misses: int = 0
    deterministic_bypasses: int = 0
    tokens_saved: int = 0
    tokens_spent: int = 0
    batches_processed: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total) if total > 0 else 0.0


class SemanticBatchCache:
    """Dual-layer SHA-256 semantic cache and deterministic bypass engine."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        max_memory_entries: int = 1000,
        default_ttl_seconds: float = 86400.0,  # 24 hours
    ) -> None:
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_memory_entries = max_memory_entries
        self.default_ttl_seconds = default_ttl_seconds
        self._memory_cache: collections.OrderedDict[str, dict[str, Any]] = collections.OrderedDict()
        self.telemetry = CacheTelemetry()

    def _compute_key(self, domain: str, payload: Any) -> str:
        """Derives a deterministic SHA-256 cache key from domain and payload."""
        if isinstance(payload, (dict, list)):
            serialized = json.dumps(payload, sort_keys=True)
        else:
            serialized = str(payload)
        digest = hashlib.sha256(f"{domain}:{serialized}".encode("utf-8")).hexdigest()
        return f"{domain}_{digest}"

    def get(self, domain: str, payload: Any) -> Any | None:
        """Retrieves value from L1 memory or L2 disk cache if unexpired."""
        key = self._compute_key(domain, payload)
        now = time.time()

        # Check L1 Memory Cache
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry["expires_at"] > now:
                self._memory_cache.move_to_end(key)
                self.telemetry.cache_hits += 1
                self.telemetry.tokens_saved += entry.get("estimated_tokens", 512)
                return entry["value"]
            del self._memory_cache[key]

        # Check L2 Disk Cache
        disk_path = self.cache_dir / f"{key}.json"
        if disk_path.exists():
            try:
                with open(disk_path, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if entry.get("expires_at", 0) > now:
                    self._put_memory(key, entry)
                    self.telemetry.cache_hits += 1
                    self.telemetry.tokens_saved += entry.get("estimated_tokens", 512)
                    return entry["value"]
                disk_path.unlink(missing_ok=True)
            except Exception as e:
                logger.debug("Disk cache read error for key %s: %s", key, e)

        self.telemetry.cache_misses += 1
        return None

    def put(
        self,
        domain: str,
        payload: Any,
        value: Any,
        estimated_tokens: int = 512,
        ttl_seconds: float | None = None,
    ) -> None:
        """Stores value in L1 memory and L2 disk cache."""
        key = self._compute_key(domain, payload)
        ttl = ttl_seconds or self.default_ttl_seconds
        expires_at = time.time() + ttl
        entry = {
            "key": key,
            "domain": domain,
            "value": value,
            "estimated_tokens": estimated_tokens,
            "created_at": time.time(),
            "expires_at": expires_at,
        }

        self._put_memory(key, entry)

        # Write to disk asynchronously or immediately
        disk_path = self.cache_dir / f"{key}.json"
        try:
            with open(disk_path, "w", encoding="utf-8") as f:
                json.dump(entry, f)
        except Exception as e:
            logger.debug("Disk cache write error for key %s: %s", key, e)

    def _put_memory(self, key: str, entry: dict[str, Any]) -> None:
        self._memory_cache[key] = entry
        self._memory_cache.move_to_end(key)
        if len(self._memory_cache) > self.max_memory_entries:
            self._memory_cache.popitem(last=False)

    def evaluate_or_bypass(
        self,
        domain: str,
        payload: Any,
        deterministic_verifier: Callable[[Any], tuple[bool, Any]],
        fallback_fn: Callable[[Any], tuple[Any, int]],
    ) -> tuple[Any, bool]:
        """First attempts deterministic AST/closed-form verification (0 tokens).
        If inapplicable, checks semantic cache.
        If cache miss, invokes fallback_fn and populates cache.
        Returns: (result, was_bypassed_or_cached)
        """
        # Step 1: Tier 0 Deterministic Check
        is_deterministic, det_result = deterministic_verifier(payload)
        if is_deterministic:
            self.telemetry.deterministic_bypasses += 1
            self.telemetry.tokens_saved += 2048  # conservative baseline saved per verifier
            return det_result, True

        # Step 2: Semantic Cache Lookup
        cached = self.get(domain, payload)
        if cached is not None:
            return cached, True

        # Step 3: Fallback invocation
        result, tokens_spent = fallback_fn(payload)
        self.telemetry.tokens_spent += tokens_spent
        self.put(domain, payload, result, estimated_tokens=tokens_spent)
        return result, False


class MicroBatcher:
    """Aggregates concurrent evaluation requests into micro-batches for efficient processing."""

    def __init__(
        self,
        batch_size: int = 8,
        flush_interval_seconds: float = 0.5,
    ) -> None:
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self._queue: list[dict[str, Any]] = []

    def add(self, item_id: str, payload: Any, metadata: dict[str, Any] | None = None) -> None:
        self._queue.append({"id": item_id, "payload": payload, "metadata": metadata or {}})

    def is_ready(self) -> bool:
        return len(self._queue) >= self.batch_size

    def flush(self) -> list[dict[str, Any]]:
        batch = list(self._queue)
        self._queue.clear()
        return batch

    def execute_batch(
        self,
        batch_processor: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Processes current pending items as a unified batch."""
        if not self._queue:
            return []
        batch = self.flush()
        return batch_processor(batch)
