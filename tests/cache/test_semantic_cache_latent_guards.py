"""cache.semantic_cache: encoder runs off the event loop and long texts fail closed."""

import asyncio
import threading

from cohezion.cache.semantic_cache import SemanticCache


def test_embedding_runs_off_the_event_loop(monkeypatch):
    seen = []

    def spy(text):
        seen.append(threading.current_thread() is threading.main_thread())

    monkeypatch.setattr(SemanticCache, "_text_to_embedding", staticmethod(spy))
    cache = SemanticCache(similarity_threshold=0.85)

    async def run():
        await cache.put("p", "r")
        await cache.get("q")

    asyncio.run(run())
    assert seen and not any(seen)


def test_text_beyond_encoder_window_returns_none():
    long_text = "word " * 400
    assert SemanticCache._text_to_embedding(long_text) is None


def test_l2_is_partitioned_by_system_prompt_and_model():
    """B3: the L2 embedding is of the prompt alone, so a different system prompt or model must
    miss; the same ones hit semantically; both partitions can hold the same prompt."""
    cache = SemanticCache(similarity_threshold=0.85)

    async def run():
        await cache.put("Delete the production database", "A-ANSWER", system="sys A", model="m1")
        other_system = await cache.get(
            "Delete the production database now", system="sys B", model="m1"
        )
        other_model = await cache.get(
            "Delete the production database now", system="sys A", model="m2"
        )
        same = await cache.get("Delete the production database now", system="sys A", model="m1")
        # a second partition with the same prompt must still be stored (novelty is per partition)
        await cache.put("Delete the production database", "B-ANSWER", system="sys B", model="m1")
        b = await cache.get("Delete the production database now", system="sys B", model="m1")
        return other_system, other_model, same, b

    other_system, other_model, same, b = asyncio.run(run())
    assert other_system is None
    assert other_model is None
    assert same == "A-ANSWER"
    assert b == "B-ANSWER"
    assert cache.hits_l2 == 2


def test_l2_partition_applies_to_get_with_observed_card():
    cache = SemanticCache(similarity_threshold=0.85)

    async def run():
        await cache.put("Delete the production database", "A", system="sys A", model="m")
        return await cache.get_with_observed_card(
            "Delete the production database now", system="sys B", model="m"
        )

    assert asyncio.run(run()) == (None, None)
