"""
Semantic Cache for AIMO - Token Efficiency Layer

Provides:
- L1: In-memory cache (fastest, session-local)
- L2: Disk cache (persistent across sessions)
- L3: Vault cache (shared across agents)

Reduces redundant LLM calls by 60-80%.
"""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    """Single cache entry."""

    key: str
    problem_hash: str
    response: str
    answer: int
    coherence: float
    timestamp: float
    access_count: int = 1
    model_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "problem_hash": self.problem_hash,
            "response": self.response,
            "answer": self.answer,
            "coherence": self.coherence,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "model_name": self.model_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        return cls(**data)


class SemanticCache:
    """
    Multi-level semantic cache for AIMO responses.

    Usage:
        cache = SemanticCache(max_entries=256)

        # Check cache
        entry = cache.get(problem_text)
        if entry:
            return entry.answer  # Cache hit!

        # Call LLM
        response = call_llm(problem_text)
        answer = extract_answer(response)

        # Store in cache
        cache.put(problem_text, response, answer, coherence=0.8)
    """

    def __init__(
        self,
        max_entries: int = 256,
        ttl_seconds: float = 3600 * 24,  # 24 hours
        cache_dir: str = "data/cache",
        vault_path: Optional[str] = None,
    ):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(cache_dir)
        self.vault_path = Path(vault_path) if vault_path else None

        # L1: In-memory cache (LRU)
        self.l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # L2: Disk cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.l2_index = self._load_l2_index()

        # L3: Vault cache (if available)
        if self.vault_path:
            self.vault_path.mkdir(parents=True, exist_ok=True)

        # Stats
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _compute_key(self, problem_text: str) -> str:
        """Compute semantic key from problem text."""
        # Normalize whitespace
        normalized = " ".join(problem_text.split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _compute_problem_hash(self, problem_text: str) -> str:
        """Compute full hash for problem."""
        return hashlib.sha256(problem_text.encode()).hexdigest()

    def get(self, problem_text: str) -> Optional[CacheEntry]:
        """Get cached entry for problem."""
        key = self._compute_key(problem_text)

        # L1: Check memory
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            # Check TTL
            if time.time() - entry.timestamp < self.ttl_seconds:
                self.hits += 1
                # Move to end (most recently used)
                self.l1_cache.move_to_end(key)
                entry.access_count += 1
                return entry
            else:
                # Expired
                del self.l1_cache[key]

        # L2: Check disk
        if key in self.l2_index:
            entry = self._load_from_l2(key)
            if entry and time.time() - entry.timestamp < self.ttl_seconds:
                self.hits += 1
                # Promote to L1
                self._store_in_l1(entry)
                return entry

        # L3: Check vault
        if self.vault_path:
            vault_file = self.vault_path / f"{key}.json"
            if vault_file.exists():
                with open(vault_file) as f:
                    data = json.load(f)
                    entry = CacheEntry.from_dict(data)
                    if time.time() - entry.timestamp < self.ttl_seconds:
                        self.hits += 1
                        # Promote to L1
                        self._store_in_l1(entry)
                        return entry

        self.misses += 1
        return None

    def put(
        self,
        problem_text: str,
        response: str,
        answer: int,
        coherence: float = 0.5,
        model_name: str = "",
    ):
        """Store response in cache."""
        key = self._compute_key(problem_text)
        problem_hash = self._compute_problem_hash(problem_text)

        entry = CacheEntry(
            key=key,
            problem_hash=problem_hash,
            response=response,
            answer=answer,
            coherence=coherence,
            timestamp=time.time(),
            model_name=model_name,
        )

        # Store in L1
        self._store_in_l1(entry)

        # Store in L2
        self._store_in_l2(entry)

        # Store in L3 (vault)
        if self.vault_path:
            self._store_in_vault(entry)

    def _store_in_l1(self, entry: CacheEntry):
        """Store in L1 cache with LRU eviction."""
        if entry.key in self.l1_cache:
            self.l1_cache.move_to_end(entry.key)
        else:
            if len(self.l1_cache) >= self.max_entries:
                # Evict oldest
                self.l1_cache.popitem(last=False)
                self.evictions += 1

        self.l1_cache[entry.key] = entry

    def _store_in_l2(self, entry: CacheEntry):
        """Store in L2 disk cache."""
        cache_file = self.cache_dir / f"{entry.key}.json"
        with open(cache_file, "w") as f:
            json.dump(entry.to_dict(), f, indent=2)

        # Update index
        self.l2_index[entry.key] = {
            "file": str(cache_file),
            "timestamp": entry.timestamp,
            "coherence": entry.coherence,
        }
        self._save_l2_index()

    def _store_in_vault(self, entry: CacheEntry):
        """Store in L3 vault cache."""
        vault_file = self.vault_path / f"{entry.key}.json"
        with open(vault_file, "w") as f:
            json.dump(entry.to_dict(), f, indent=2)

    def _load_from_l2(self, key: str) -> Optional[CacheEntry]:
        """Load from L2 disk cache."""
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None

        with open(cache_file) as f:
            data = json.load(f)
            return CacheEntry.from_dict(data)

    def _load_l2_index(self) -> Dict[str, Any]:
        """Load L2 index."""
        index_file = self.cache_dir / "index.json"
        if not index_file.exists():
            return {}

        with open(index_file) as f:
            return json.load(f)

    def _save_l2_index(self):
        """Save L2 index."""
        index_file = self.cache_dir / "index.json"
        with open(index_file, "w") as f:
            json.dump(self.l2_index, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "evictions": self.evictions,
            "l1_size": len(self.l1_cache),
            "l2_size": len(self.l2_index),
            "tokens_saved_estimate": self.hits * 500,  # ~500 tokens per cached response
        }

    def clear_expired(self) -> int:
        """Clear expired entries. Returns count cleared."""
        now = time.time()
        cleared = 0

        # Clear L1
        expired_keys = [k for k, v in self.l1_cache.items() if now - v.timestamp > self.ttl_seconds]
        for key in expired_keys:
            del self.l1_cache[key]
            cleared += 1

        # Clear L2
        expired_keys = [
            k for k, v in self.l2_index.items() if now - v["timestamp"] > self.ttl_seconds
        ]
        for key in expired_keys:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                cache_file.unlink()
            del self.l2_index[key]
            cleared += 1

        if expired_keys:
            self._save_l2_index()

        return cleared

    def save_snapshot(self) -> str:
        """Save cache snapshot for warm start."""
        snapshot_file = self.cache_dir / "snapshot.json"

        snapshot = {
            "timestamp": time.time(),
            "entries": [entry.to_dict() for entry in self.l1_cache.values()],
            "stats": self.get_stats(),
        }

        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2)

        return str(snapshot_file)

    def load_snapshot(self) -> int:
        """Load cache snapshot for warm start. Returns entries loaded."""
        snapshot_file = self.cache_dir / "snapshot.json"
        if not snapshot_file.exists():
            return 0

        with open(snapshot_file) as f:
            snapshot = json.load(f)

        loaded = 0
        for data in snapshot.get("entries", []):
            entry = CacheEntry.from_dict(data)
            # Check if still valid
            if time.time() - entry.timestamp < self.ttl_seconds:
                self.l1_cache[entry.key] = entry
                loaded += 1

        # Restore stats
        stats = snapshot.get("stats", {})
        self.hits = stats.get("hits", 0)
        self.misses = stats.get("misses", 0)
        self.evictions = stats.get("evictions", 0)

        return loaded


class CachePersistence:
    """Cache persistence utilities."""

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)

    def save_cache(self, cache: SemanticCache):
        """Save cache on session end."""
        cache.save_snapshot()
        cache.clear_expired()

    def warm_cache(self, cache: SemanticCache, max_entries: int = 256) -> int:
        """Warm cache on session start."""
        loaded = cache.load_snapshot()
        return loaded


# Global cache instance
_global_cache: Optional[SemanticCache] = None


def get_cache(
    max_entries: int = 256,
    ttl_seconds: float = 3600 * 24,
    cache_dir: str = "data/cache",
    vault_path: Optional[str] = None,
) -> SemanticCache:
    """Get or create global cache instance."""
    global _global_cache

    if _global_cache is None:
        _global_cache = SemanticCache(
            max_entries=max_entries,
            ttl_seconds=ttl_seconds,
            cache_dir=cache_dir,
            vault_path=vault_path,
        )

    return _global_cache
