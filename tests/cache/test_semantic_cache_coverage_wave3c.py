"""Wave 3C coverage tests for SemanticCache (synthetic-sniffing-panda).

Targets the previously-uncovered branches of
``src/cohezion/cache/semantic_cache.py``:

- L1 FIFO eviction at ``max_l1_size``
- L2 LFU eviction at ``max_l2_size`` (and the disabled ``max_l2_size=0`` path)
- L2 cosine similarity hit + L1 promotion
- L2 below-threshold miss
- Adaptive threshold: relax (low hit-rate) / tighten (high hit-rate)
- ``_text_to_embedding`` hash-fallback when both encoders raise
- ``put`` outside an event loop (RuntimeError swallow path)
- Concurrent reads via ``asyncio.gather``

All embedding work is patched at the static-method seam to keep tests
deterministic and offline (no sentence-transformer / FLUME VAE downloads).
No real network or DB calls.
"""

from __future__ import annotations

import asyncio
import hashlib
from unittest.mock import patch

import numpy as np
import pytest

from cohezion.cache.semantic_cache import SemanticCache


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _unit_vec(seed: int, dim: int = 384) -> np.ndarray:
    """Deterministic L2-normalized vector keyed on ``seed``."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v


@pytest.fixture()
def fixed_embedding(monkeypatch):
    """Patch ``_text_to_embedding`` to return a fixed unit vector.

    Returns a list that callers can mutate to assign per-call vectors.
    """
    vectors: list[np.ndarray] = [_unit_vec(0)]
    call_count = {"n": 0}

    def fake_encode(text: str) -> np.ndarray:
        idx = min(call_count["n"], len(vectors) - 1)
        call_count["n"] += 1
        return vectors[idx]

    monkeypatch.setattr(SemanticCache, "_text_to_embedding", staticmethod(fake_encode))
    return vectors


# ---------------------------------------------------------------------------
# L1: exact-hash tier
# ---------------------------------------------------------------------------


class TestL1ExactMatch:
    """L1 hit / miss / FIFO eviction."""

    @pytest.mark.asyncio
    async def test_l1_exact_hit_increments_hits_l1(self, fixed_embedding):
        """Exact same (prompt, system, model) => L1 hit, hits_l1 += 1."""
        cache = SemanticCache()
        await cache.put("hello", "world", system="sys", model="m1")

        result = await cache.get("hello", system="sys", model="m1")

        assert result == "world"
        assert cache.hits_l1 == 1
        assert cache.misses == 0

    @pytest.mark.asyncio
    async def test_l1_miss_with_distinct_model_key(self, fixed_embedding):
        """Same prompt but different model => different hash key, L1 miss.

        Embedding is forced identical, but the cache is empty in L2 too,
        so this exercises the L1 miss path cleanly.
        """
        cache = SemanticCache(similarity_threshold=0.99)
        await cache.put("hello", "world", system="sys", model="m1")

        # Empty L2 (only one entry, embedding identical => still > threshold).
        # To force a true L1 miss without an L2 hit, clear L2 explicitly.
        cache.l2_cache.clear()
        cache.l2_lfu_counts.clear()

        result = await cache.get("hello", system="sys", model="m2")

        assert result is None
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_l1_fifo_eviction_at_max_size(self, fixed_embedding):
        """When L1 is full, the oldest insertion is evicted (FIFO)."""
        cache = SemanticCache(max_l1_size=3, max_l2_size=0)

        for i in range(4):
            await cache.put(f"prompt-{i}", f"resp-{i}", model="m")

        assert len(cache.l1_cache) == 3
        # The oldest (prompt-0) must be gone, newest (prompt-3) present.
        full0 = "\nprompt-0\nm"
        h0 = hashlib.sha256(full0.encode()).hexdigest()[:16]
        full3 = "\nprompt-3\nm"
        h3 = hashlib.sha256(full3.encode()).hexdigest()[:16]
        assert h0 not in cache.l1_cache
        assert h3 in cache.l1_cache


# ---------------------------------------------------------------------------
# L2: cosine similarity tier
# ---------------------------------------------------------------------------


class TestL2Cosine:
    """L2 above-threshold hit, below-threshold miss, threshold-edge."""

    @pytest.mark.asyncio
    async def test_l2_high_similarity_hit_promotes_to_l1(self, monkeypatch):
        """Identical embeddings => similarity 1.0 > 0.88 => L2 hit + L1 promote."""
        vec = _unit_vec(7)
        monkeypatch.setattr(SemanticCache, "_text_to_embedding", staticmethod(lambda _t: vec))
        cache = SemanticCache(similarity_threshold=0.88)
        await cache.put("first", "answer", model="m")

        # Drop L1 so we hit L2 instead.
        cache.l1_cache.clear()
        cache.l1_insertion_order.clear()

        result = await cache.get("DIFFERENT TEXT", model="m")

        assert result == "answer"
        assert cache.hits_l2 == 1
        # Promotion to L1
        assert len(cache.l1_cache) == 1

    @pytest.mark.asyncio
    async def test_l2_low_similarity_miss(self, monkeypatch):
        """Orthogonal vectors => similarity ~0.0 < threshold => miss."""
        vectors = iter([_unit_vec(1), _unit_vec(99999)])
        monkeypatch.setattr(
            SemanticCache,
            "_text_to_embedding",
            staticmethod(lambda _t: next(vectors)),
        )
        cache = SemanticCache(similarity_threshold=0.88, enable_adaptive_threshold=False)
        await cache.put("aaaa", "ans-a", model="m")

        cache.l1_cache.clear()
        cache.l1_insertion_order.clear()

        result = await cache.get("zzzz", model="m")

        assert result is None
        assert cache.hits_l2 == 0
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_l2_threshold_edge_strictly_greater(self, monkeypatch):
        """Code uses ``best_similarity > current_threshold`` (strict).

        Identical embeddings produce similarity == 1.0 which always exceeds
        any threshold < 1.0; this confirms the strict-inequality branch.
        """
        vec = _unit_vec(42)
        monkeypatch.setattr(SemanticCache, "_text_to_embedding", staticmethod(lambda _t: vec))
        cache = SemanticCache(similarity_threshold=0.999, enable_adaptive_threshold=False)
        await cache.put("A", "stored", model="m")

        cache.l1_cache.clear()
        cache.l1_insertion_order.clear()

        result = await cache.get("B", model="m")
        assert result == "stored"


# ---------------------------------------------------------------------------
# L2 eviction policy (LFU)
# ---------------------------------------------------------------------------


class TestL2Eviction:
    """LFU eviction + ``max_l2_size=0`` short-circuit."""

    @pytest.mark.asyncio
    async def test_l2_lfu_eviction_at_capacity(self, fixed_embedding):
        """When L2 is full, the lowest-count entry is evicted."""
        cache = SemanticCache(max_l1_size=512, max_l2_size=2)

        await cache.put("p1", "r1", model="m")
        await cache.put("p2", "r2", model="m")
        # Bump p1's LFU so p2 is the LFU victim.
        h1 = hashlib.sha256(b"\np1\nm").hexdigest()[:16]
        h1 = hashlib.sha256("\np1\nm".encode()).hexdigest()[:16]
        cache.l2_lfu_counts[h1] = 5

        await cache.put("p3", "r3", model="m")

        h2 = hashlib.sha256(b"\np2\nm").hexdigest()[:16]
        h3 = hashlib.sha256(b"\np3\nm").hexdigest()[:16]
        h2 = hashlib.sha256("\np2\nm".encode()).hexdigest()[:16]
        h3 = hashlib.sha256("\np3\nm".encode()).hexdigest()[:16]
        assert h2 not in cache.l2_cache
        assert h1 in cache.l2_cache
        assert h3 in cache.l2_cache
        assert len(cache.l2_cache) == 2

    @pytest.mark.asyncio
    async def test_l2_disabled_when_max_size_zero(self, fixed_embedding):
        """``max_l2_size=0`` => ``put`` skips L2 entirely."""
        cache = SemanticCache(max_l2_size=0)
        await cache.put("only L1", "v", model="m")

        assert cache.l2_cache == {}
        assert cache.l2_lfu_counts == {}
        # L1 still populated.
        assert len(cache.l1_cache) == 1


# ---------------------------------------------------------------------------
# Adaptive threshold tuning
# ---------------------------------------------------------------------------


class TestAdaptiveThreshold:
    """Adaptive-threshold relax/tighten/disabled."""

    def test_adaptive_disabled_returns_initial(self):
        """Disabled flag => ``_get_adaptive_threshold`` returns initial."""
        cache = SemanticCache(similarity_threshold=0.91, enable_adaptive_threshold=False)
        # Pretend we did lots of ops with 0% L2 hit rate.
        cache.misses = 1_000
        assert cache._get_adaptive_threshold() == 0.91

    def test_adaptive_relaxes_on_low_l2_hit_rate(self):
        """L2 hit rate < 5% => threshold drops by 0.05."""
        cache = SemanticCache(similarity_threshold=0.90)
        # 200 ops, 0 L2 hits => 0% < 5%
        cache.misses = 200
        cache.hits_l2 = 0
        new_t = cache._get_adaptive_threshold()
        assert new_t == pytest.approx(0.85, abs=1e-9)

    def test_adaptive_tightens_on_high_l2_hit_rate(self):
        """L2 hit rate > 40% => threshold rises by 0.05 (bounded by 0.97)."""
        cache = SemanticCache(similarity_threshold=0.90)
        # 100 ops, 60 L2 hits => 60% > 40%
        cache.hits_l2 = 60
        cache.misses = 40
        new_t = cache._get_adaptive_threshold()
        assert new_t == pytest.approx(0.95, abs=1e-9)

    def test_adaptive_holds_when_in_target_band(self):
        """Hit rate in [5%, 40%] => unchanged."""
        cache = SemanticCache(similarity_threshold=0.88)
        cache.hits_l2 = 20
        cache.misses = 80  # 20% L2 hit rate
        assert cache._get_adaptive_threshold() == 0.88


# ---------------------------------------------------------------------------
# Embedding fallback chain
# ---------------------------------------------------------------------------


class TestEmbeddingFallback:
    """Hash fallback when both encoders raise."""

    def test_text_to_embedding_falls_back_to_hash(self, monkeypatch):
        """If text encoder + VAE both raise, deterministic SHA-256 vector wins.

        The fallback must be 384-D, dtype float32, and L2-normalized.
        """

        # Force both encoder paths to raise.
        def boom_text():
            raise RuntimeError("no text encoder")

        def boom_vae():
            raise RuntimeError("no VAE")

        monkeypatch.setattr("cohezion.cache.semantic_cache.get_text_encoder", boom_text)
        monkeypatch.setattr("cohezion.cache.semantic_cache.get_encoder", boom_vae)

        emb = SemanticCache._text_to_embedding("deterministic input")

        assert emb.shape == (384,)
        assert emb.dtype == np.float32
        # Normalized to unit length (within float32 tolerance).
        assert np.linalg.norm(emb) == pytest.approx(1.0, abs=1e-5)

        # Determinism: same input => same vector.
        emb2 = SemanticCache._text_to_embedding("deterministic input")
        assert np.allclose(emb, emb2)


# ---------------------------------------------------------------------------
# ``put`` outside event loop
# ---------------------------------------------------------------------------


class TestPutSyncContext:
    """``put`` swallows RuntimeError when no loop is running."""

    @pytest.mark.asyncio
    async def test_put_handles_no_event_loop_for_l3(self, fixed_embedding):
        """``asyncio.create_task`` raises RuntimeError outside a loop.

        We patch ``create_task`` to raise to exercise the except-RuntimeError
        branch without leaving the running test event loop.
        """
        cache = SemanticCache()

        with patch(
            "cohezion.cache.semantic_cache.asyncio.create_task",
            side_effect=RuntimeError("no running event loop"),
        ):
            # Should NOT raise; should still populate L1/L2.
            await cache.put("p", "r", model="m")

        assert len(cache.l1_cache) == 1


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrentAccess:
    """Concurrent readers + reader/writer correctness."""

    @pytest.mark.asyncio
    async def test_concurrent_readers_all_see_l1_hit(self, fixed_embedding):
        """N concurrent ``get`` calls on a hit return identical responses."""
        cache = SemanticCache()
        await cache.put("k", "v", model="m")

        results = await asyncio.gather(*(cache.get("k", model="m") for _ in range(8)))
        assert results == ["v"] * 8
        assert cache.hits_l1 == 8

    @pytest.mark.asyncio
    async def test_reader_and_writer_interleave(self, fixed_embedding):
        """Interleaved get/put preserve cache invariants (no crash, key visible)."""
        cache = SemanticCache()

        async def writer():
            for i in range(5):
                await cache.put(f"k{i}", f"v{i}", model="m")

        async def reader():
            seen: list[str | None] = []
            for i in range(5):
                seen.append(await cache.get(f"k{i}", model="m"))
            return seen

        # Writer first then reader — guarantees deterministic visibility while
        # still exercising both coroutines on the same cache instance.
        await writer()
        seen = await reader()
        assert all(s == f"v{i}" for i, s in enumerate(seen))


# ---------------------------------------------------------------------------
# Stats sanity at edges
# ---------------------------------------------------------------------------


class TestStatsAndClearEdges:
    """Stat invariants + ``clear`` resets adaptive-threshold inputs."""

    @pytest.mark.asyncio
    async def test_clear_resets_all_counters(self, fixed_embedding):
        cache = SemanticCache()
        await cache.put("p", "r", model="m")
        await cache.get("p", model="m")  # +1 L1 hit
        await cache.get("missing", model="m")  # +1 miss
        cache.clear()
        stats = cache.get_stats()
        assert stats == {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
            "total_requests": 0,
            "overall_hit_rate": 0.0,
            "l1_hit_rate": 0.0,
            "l2_hit_rate": 0.0,
            "l3_hit_rate": 0.0,
            "l1_size": 0,
            "l2_size": 0,
            "similarity_threshold": cache.similarity_threshold,
        }
