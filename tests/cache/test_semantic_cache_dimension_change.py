"""Encoder dimension change must not crash the L2 semantic tier.

``SemanticCache._text_to_embedding`` walks an encoder ladder (nomic 768D, MiniLM 384D,
FLUME 256D, hash 384D) whose availability changes at runtime: Lemonade going down
mid-process silently moves every new embedding to a different width. The L2 tier keeps
ONE stacked similarity matrix, so the first lookup or insert after the switch called
``np.dot(matrix_768, query_384)`` and raised ``ValueError: shapes not aligned`` inside
the api's request path.

The fix flushes L2 rows whose width differs from the incoming embedding. These tests
drive the real ``get``/``put`` path with a scripted encoder; the only seam patched is
``_text_to_embedding`` (where the width comes from).
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from cohezion.cache.semantic_cache import SemanticCache


pytestmark = pytest.mark.asyncio


def _unit(dim: int, seed: int) -> np.ndarray:
    v = np.random.default_rng(seed).standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def cache() -> SemanticCache:
    # Non-default threshold: skips the encoder auto-tune probe in __init__.
    return SemanticCache(similarity_threshold=0.5, enable_adaptive_threshold=False)


def _encoder(widths: list[int]):
    """Scripted encoder: the n-th call returns a unit vector of widths[n]."""
    calls = iter(enumerate(widths))

    def fake(_text: str) -> np.ndarray:
        i, dim = next(calls)
        return _unit(dim, i)

    return fake


async def test_lookup_after_encoder_width_change_does_not_crash(cache):
    with patch.object(SemanticCache, "_text_to_embedding", side_effect=_encoder([768, 384])):
        await cache.put("first prompt", "first response")
        assert cache._l2_matrix is not None and cache._l2_matrix.shape[1] == 768

        # Different prompt -> L1 miss -> L2 dot product against the 768D matrix.
        result = await cache.get("a completely different prompt")

    assert result is None  # a miss, not a ValueError
    # The incompatible 768D rows are gone; nothing of the old width survives.
    assert cache._l2_matrix is None or cache._l2_matrix.shape[1] == 384


async def test_insert_after_encoder_width_change_keeps_only_new_width(cache):
    with patch.object(SemanticCache, "_text_to_embedding", side_effect=_encoder([768, 384])):
        await cache.put("first prompt", "first response")
        await cache.put("second prompt", "second response")

    assert cache._l2_matrix is not None
    assert cache._l2_matrix.shape == (1, 384)
    assert all(e.embedding.shape == (384,) for e in cache.l2_cache.values())
    assert set(cache.l2_lfu_counts) <= set(cache.l2_cache)


async def test_same_width_entries_are_not_flushed(cache):
    """Discriminating: a flush-everything implementation would empty L2 here."""
    with patch.object(SemanticCache, "_text_to_embedding", side_effect=_encoder([384, 384])):
        await cache.put("first prompt", "first response")
        await cache.put("second prompt", "second response")

    assert cache._l2_matrix is not None and cache._l2_matrix.shape == (2, 384)
