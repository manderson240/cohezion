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
