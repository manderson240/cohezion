# ruff: noqa: F811
"""B2 (window guard on identity callers) and the to_thread / encode_or_none strengthening tests
(M8a/b/c, M14b/c). Plain tests, not requires_real_st: they inject a real-tokenizer
`_load_minilm` via test_canonical_latent_concurrency, so they run under the mocked suite."""

from __future__ import annotations

import asyncio
import threading
import types

import numpy as np

from cohezion.flume.canonical_latent import CanonicalTextLatent
from tests.flume.test_canonical_latent_concurrency import LONG_A, LONG_B, real_loader  # noqa: F401


def test_strict_window_returns_none_beyond_window_and_counts(real_loader):
    enc = CanonicalTextLatent(real_loader)
    assert enc.encode_or_none("w1 w2", strict_window=True) is not None
    before = enc.skipped_calls
    assert enc.encode_or_none(LONG_A, strict_window=True) is None
    assert enc.skipped_calls == before + 1
    # default contract unchanged: long text is still embedded (from its head)
    assert enc.encode_or_none(LONG_A) is not None


def _agent(tmp_path, encoder):
    from types import SimpleNamespace

    from cohezion.agents.base import BaseAgent

    class _A(BaseAgent):
        async def process(self, *a, **k):
            return None

    class _Mem:
        def __init__(self):
            self.rows = []

        async def add(self, vector, response, metadata, query_text=None, scope=None):
            self.rows.append((np.asarray(vector), response))

        async def search(self, vector, query_text=None, scope=None):
            for v, r in self.rows:
                if float(np.dot(v, vector)) > 0.95:
                    return {"response": r, "semantic_score": 1.0}
            return None

    agent = object.__new__(_A)
    agent.model_name = "m"
    agent.cache_dir = tmp_path
    agent.config = SimpleNamespace(cache_ttl_seconds=3600)
    agent._metrics = {"cache_hits": 0}
    agent._semantic_cache = _Mem()
    agent._encoder = encoder
    return agent


def test_base_agent_does_not_serve_other_prompts_answer_past_window(tmp_path, real_loader):
    """B2: two prompts sharing their first WINDOW tokens must not hit each other."""
    enc = CanonicalTextLatent(real_loader)
    agent = _agent(tmp_path, enc)

    async def run():
        await agent._set_cached(LONG_A, "ANSWER-A")
        return await agent._get_cached(LONG_B)

    assert asyncio.run(run()) is None
    assert agent._semantic_cache.rows == []  # nothing stored under the truncated head either


def test_base_agent_short_prompt_still_hits_semantically(tmp_path, real_loader):
    enc = CanonicalTextLatent(real_loader)
    agent = _agent(tmp_path, enc)

    async def run():
        await agent._set_cached("w1 w2 w3", "ANSWER")
        agent._cache_key = lambda p, images=None: "other-" + p  # defeat the exact-file hit
        return await agent._get_cached("w1 w2 w3")

    assert asyncio.run(run())["response"] == "ANSWER"


def _dead() -> CanonicalTextLatent:
    def loader():
        raise OSError("weights missing")

    return CanonicalTextLatent(loader)


def test_base_agent_get_and_set_do_not_raise_when_latent_unavailable(tmp_path):
    """M8a: swapping encode_or_none for encode in _semantic_vector would raise here."""
    agent = _agent(tmp_path, _dead())

    async def run():
        await agent._set_cached("p", "r")
        return await agent._get_cached("q")

    assert asyncio.run(run()) is None


def test_base_agent_encodes_off_the_event_loop(tmp_path, real_loader):
    """M14b: removing asyncio.to_thread around _semantic_vector puts it on the loop thread."""
    agent = _agent(tmp_path, CanonicalTextLatent(real_loader))
    seen: list[bool] = []
    orig = agent._semantic_vector

    def spy(text):
        seen.append(threading.current_thread() is threading.main_thread())
        return orig(text)

    agent._semantic_vector = spy

    async def run():
        await agent._set_cached("w1 w2", "r")
        await agent._get_cached("w3 w4")

    asyncio.run(run())
    assert len(seen) >= 2 and not any(seen)


def test_cache_text_to_embedding_is_none_when_latent_unavailable(monkeypatch):
    """M8b: encode instead of encode_or_none in cache/semantic_cache would raise."""
    from cohezion.cache import semantic_cache as sc

    monkeypatch.setattr(sc, "get_encoder", _dead)
    assert sc.SemanticCache._text_to_embedding("anything") is None


def test_cache_get_put_off_loop_on_every_path(monkeypatch):
    """M14c: get, get_with_observed_card, put (with and without card) and the L3 path all embed
    off the loop thread."""
    from cohezion.cache.semantic_cache import SemanticCache

    seen: list[bool] = []

    def spy(text):
        seen.append(threading.current_thread() is threading.main_thread())

    monkeypatch.setattr(SemanticCache, "_text_to_embedding", staticmethod(spy))
    cache = SemanticCache(similarity_threshold=0.85)

    async def _vault(_prompt):
        return "from-vault"

    monkeypatch.setattr(cache, "_vault_lookup", _vault)

    async def run():
        card = ("m", "f", "t")
        await cache.put("p", "r")
        await cache.put("p2", "r2", model="m", card_signature=card)
        await cache.get("q")  # miss L1/L2 -> L3 path embeds too
        await cache.get_with_observed_card("q2", model="m", card_signature=card)

    asyncio.run(run())
    assert len(seen) >= 5 and not any(seen), seen


def test_journey_logger_survives_unavailable_latent():
    """M8c: encode instead of encode_or_none in platform loggers would raise."""
    from unittest.mock import AsyncMock, MagicMock

    from cohezion.platform.journey_logger import JourneyLogger

    jl = object.__new__(JourneyLogger)
    jl.db = MagicMock()
    jl.db.query = AsyncMock()
    jl.vae = _dead()
    jl.coherence_tracker = MagicMock()
    jl.coherence_tracker.measure_system_coherence = AsyncMock(
        return_value=types.SimpleNamespace(coherence=0.5)
    )
    jid = asyncio.run(jl.start_journey("t", "ctx"))
    assert jid
    assert jl.db.query.await_args.args[1]["flume_state"] == []
