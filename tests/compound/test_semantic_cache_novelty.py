"""Tests for SemanticCache novelty gate (Task #94)."""

import asyncio

import numpy as np

from cohezion.cache.semantic_cache import SemanticCache


def _unit_vector(dim: int = 384, index: int = 0) -> np.ndarray:
    """Return a unit vector with 1.0 at position `index`."""
    v = np.zeros(dim, dtype=np.float32)
    v[index] = 1.0
    return v


class TestNoveltyGate:
    """Discriminating tests for the L2 novelty gate."""

    def test_same_embedding_twice_second_skipped(self):
        """T1: Inserting the same embedding twice must skip the second (novelty_skipped=1).

        Wrong implementation: always insert regardless — would give novelty_skipped=0.
        This test discriminates the correct gate from the no-op.
        """
        cache = SemanticCache(novelty_threshold=0.95)

        embedding = _unit_vector()

        # Patch _text_to_embedding so we control the embeddings exactly
        call_count = 0

        def fake_embed(text: str) -> np.ndarray:
            nonlocal call_count
            call_count += 1
            return embedding.copy()

        cache._text_to_embedding = staticmethod(fake_embed)  # type: ignore[method-assign]

        asyncio.run(cache.put("prompt_a", "response_a"))
        asyncio.run(cache.put("prompt_b", "response_b"))

        stats = cache.get_stats()
        assert stats["novelty_skipped"] == 1, (
            f"Expected novelty_skipped=1 but got {stats['novelty_skipped']}. "
            "Second insertion of an identical embedding should be skipped."
        )
        assert stats["l2_size"] == 1, (
            f"Expected l2_size=1 (only first entry stored) but got {stats['l2_size']}."
        )

    def test_distinct_embeddings_both_inserted(self):
        """T2: Distinct (orthogonal) embeddings must both be inserted (novelty_skipped=0).

        Wrong implementation: always skip second insert — would give novelty_skipped=1.
        This test discriminates the correct gate from an overly aggressive blocker.
        """
        cache = SemanticCache(novelty_threshold=0.95)

        embed_a = _unit_vector(index=0)
        embed_b = _unit_vector(index=1)  # orthogonal: cosine similarity = 0.0
        embeddings = [embed_a, embed_b]
        call_idx = 0

        def fake_embed(text: str) -> np.ndarray:
            nonlocal call_idx
            result = embeddings[call_idx % len(embeddings)]
            call_idx += 1
            return result.copy()

        cache._text_to_embedding = staticmethod(fake_embed)  # type: ignore[method-assign]

        asyncio.run(cache.put("prompt_a", "response_a"))
        asyncio.run(cache.put("prompt_b", "response_b"))

        stats = cache.get_stats()
        assert stats["novelty_skipped"] == 0, (
            f"Expected novelty_skipped=0 but got {stats['novelty_skipped']}. "
            "Orthogonal embeddings should both be inserted."
        )
        assert stats["l2_size"] == 2, (
            f"Expected l2_size=2 (both entries stored) but got {stats['l2_size']}."
        )
