# ruff: noqa: F811
"""F1/F2: the reliability semantic cache is scoped and every tier's hit survives _call_ollama.

These go through the REAL reliability SemanticCache (fake Redis only) and the real
BaseAgent._call_ollama; only the model call (router.LOCAL_ROUTER.route_task) is stubbed, and it
counts calls so "served from cache" and "asked the model" are distinguishable.
"""

from __future__ import annotations

import asyncio
import hashlib
import zlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from cohezion.agents import base as base_mod
from cohezion.agents.base import BaseAgent
from cohezion.flume.canonical_latent import CanonicalTextLatent
from cohezion.reliability.semantic_cache import SemanticCache, query_digest
from cohezion.swarm.swarm_types import SwarmConfig
from tests.flume.test_canonical_latent_concurrency import LONG_A, real_loader  # noqa: F401


SAVINGS = "Move $100 from savings to checking"
CHECKING = "Move $100 from checking to savings"  # direction-reversed


class FakeRedis:
    def __init__(self):
        self.d: dict = {}

    async def get(self, key):
        return self.d.get(key)

    async def set(self, key, value, ttl=None):
        self.d[key] = value


class NullRedis(FakeRedis):
    async def set(self, key, value, ttl=None):
        return None


def _latent() -> CanonicalTextLatent:
    """Raw vectors by text: the reversed pair is near-identical (cosine ~0.99, like MiniLM),
    everything else is pseudo-random and unrelated."""
    base = np.random.default_rng(1).standard_normal(384).astype(np.float32)
    near = base + 0.05 * np.random.default_rng(2).standard_normal(384).astype(np.float32)

    def embed(text: str) -> np.ndarray:
        if text == SAVINGS:
            return base
        if text == CHECKING:
            return near
        rng = np.random.default_rng(zlib.crc32(text.encode()))
        return rng.standard_normal(384).astype(np.float32)

    return CanonicalTextLatent(lambda: embed)


class AgentA(BaseAgent):
    async def process(self, *a, **k):
        return None


class AgentB(BaseAgent):
    async def process(self, *a, **k):
        return None


@pytest.fixture
def world(tmp_path, monkeypatch):
    import cohezion.core.routing.router as router
    import cohezion.learning.recorder as recorder

    monkeypatch.chdir(tmp_path)
    tk = MagicMock()
    tk.log_event = AsyncMock()
    monkeypatch.setattr(base_mod, "get_time_keeper", lambda: tk)
    acc = MagicMock()
    acc.add_experience = AsyncMock()
    monkeypatch.setattr(base_mod, "get_accumulator", lambda: acc)
    monkeypatch.setattr(recorder, "get_learning_recorder", lambda: MagicMock())
    calls: list[str] = []

    async def route_task(*a, **k):
        calls.append(k.get("prompt") or str(a))
        return f"fresh-{len(calls)}"

    monkeypatch.setattr(router.LOCAL_ROUTER, "route_task", route_task)

    cache = SemanticCache(cache_dir=str(tmp_path / "shared-sem"), threshold=0.95)
    cache.redis = FakeRedis()
    cache._vault = SimpleNamespace(get_experience_guidance=lambda q: None)
    latent = _latent()
    n = {"i": 0}

    def make(cls=AgentA, model="model-a", shared=cache):
        n["i"] += 1  # own file-cache dir: only the SHARED semantic/Redis tiers can hit
        agent = cls(
            model,
            config=SwarmConfig(mrp_sync=False),
            cache_dir=tmp_path / f"files-{n['i']}",
        )
        agent._semantic_cache = shared
        agent._encoder = latent
        agent.self_evaluate = AsyncMock(return_value=(1.0, 1.0, {}))
        return agent

    return SimpleNamespace(make=make, cache=cache, calls=calls, tmp=tmp_path)


def _ask(agent, prompt, system="sys"):
    return asyncio.run(agent._call_ollama(prompt, system_prompt=system))


def _drop_local(cache):
    cache.vectors, cache.metadata = [], []


# ---- F2: scope ---------------------------------------------------------------------------------


def test_same_scope_exact_prompt_is_served_from_semantic_tier(world):
    _ask(world.make(), SAVINGS)
    n = len(world.calls)
    world.cache.redis = FakeRedis()  # force the vector tier, not Redis L1
    out = _ask(world.make(), SAVINGS)
    assert str(out) == "fresh-1" and len(world.calls) == n


@pytest.mark.parametrize(
    "other",
    [{"model": "model-b"}, {"cls": AgentB}],
    ids=["other-model", "other-agent-class"],
)
@pytest.mark.parametrize("tier", ["redis", "vectors-only"])
def test_other_model_or_agent_never_gets_the_answer(world, other, tier):
    _ask(world.make(), SAVINGS)
    if tier == "vectors-only":
        world.cache.redis = FakeRedis()
    n = len(world.calls)
    out = _ask(world.make(**other), SAVINGS)
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_other_system_prompt_never_gets_the_answer(world):
    _ask(world.make(), SAVINGS, system="You are a bank bot")
    n = len(world.calls)
    out = _ask(world.make(), SAVINGS, system="Totally different persona: pirate")
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_direction_reversed_prompt_is_not_served(world):
    """Embedding limit: the reversed instruction sits at cosine ~0.99 of the original, so only
    exact-match serving keeps the wrong answer out. A scope fix alone would not."""
    _ask(world.make(), SAVINGS)
    agent = world.make()
    v1, v2 = agent._semantic_vector(SAVINGS), agent._semantic_vector(CHECKING)
    assert float(np.dot(v1, v2)) > 0.95  # precondition: the encoder cannot tell them apart
    n = len(world.calls)
    out = _ask(agent, CHECKING)
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_prompts_sharing_their_first_500_chars_are_not_confused(world):
    head = "x " * 260
    a, b = head + "ALPHA", head + "BETA"
    assert a[:500] == b[:500]
    _ask(world.make(), a)
    n = len(world.calls)
    out = _ask(world.make(), b)
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_unscoped_and_legacy_entries_are_never_served(world):
    cache = world.cache
    vec = world.make()._semantic_vector(SAVINGS)
    asyncio.run(cache.add(vec, "LEGACY", {"prompt": SAVINGS}, query_text=SAVINGS))  # no scope
    assert asyncio.run(cache.search(vec, query_text=SAVINGS, scope="s")) is None
    assert asyncio.run(cache.search(vec, query_text=SAVINGS)) is None  # no scope = refused
    # an old v1 Redis key (sha256 of the query only) holding a stranger's answer
    cache.redis.d["semantic_cache:exact:" + hashlib.sha256(SAVINGS.encode()).hexdigest()] = {
        "response": "V1-LEAK",
        "semantic_score": 1.0,
    }
    assert asyncio.run(cache.search(vec, query_text=SAVINGS, scope="s")) is None


def test_two_scopes_same_response_text_keep_separate_entries(world):
    cache = world.cache
    vec = world.make()._semantic_vector(SAVINGS)
    asyncio.run(cache.add(vec, "OK", {}, query_text=SAVINGS, scope="s1"))
    asyncio.run(cache.add(vec, "OK", {}, query_text=SAVINGS, scope="s2"))
    assert sorted(m["scope"] for m in cache.metadata) == ["s1", "s2"]
    assert asyncio.run(cache.search(vec, query_text=SAVINGS, scope="s1"))["scope"] == "s1"
    assert asyncio.run(cache.search(vec, query_text=SAVINGS, scope="s2"))["scope"] == "s2"


def test_redis_keeps_one_slot_per_scope(world):
    """Two scopes, same query text: after dropping the local vectors, each scope still reads
    its own answer from Redis L1 (a key without the scope would let the second overwrite)."""
    cache = world.cache
    vec = world.make()._semantic_vector(SAVINGS)
    asyncio.run(cache.add(vec, "ANS-1", {}, query_text=SAVINGS, scope="s1"))
    asyncio.run(cache.add(vec, "ANS-2", {}, query_text=SAVINGS, scope="s2"))
    _drop_local(cache)
    assert asyncio.run(cache.search(vec, query_text=SAVINGS, scope="s1"))["response"] == "ANS-1"
    assert asyncio.run(cache.search(vec, query_text=SAVINGS, scope="s2"))["response"] == "ANS-2"


def test_redis_value_from_another_scope_is_rejected(world):
    cache = world.cache
    vec = world.make()._semantic_vector(SAVINGS)
    cache.redis.d[cache._redis_key("s1", SAVINGS)] = {
        "response": "WRONG",
        "scope": "s2",
        "query_digest": query_digest(SAVINGS),
    }
    assert asyncio.run(cache.search(vec, query_text=SAVINGS, scope="s1")) is None


def test_fuzzy_mode_is_opt_in_and_scope_bounded(world, tmp_path):
    """exact_only=False restores paraphrase serving (and its wrong answers) inside one scope."""
    fuzzy = SemanticCache(cache_dir=str(tmp_path / "fz"), threshold=0.95, exact_only=False)
    fuzzy.redis = FakeRedis()
    fuzzy._vault = SimpleNamespace(get_experience_guidance=lambda q: None)
    agent = world.make()
    v1, v2 = agent._semantic_vector(SAVINGS), agent._semantic_vector(CHECKING)
    asyncio.run(fuzzy.add(v1, "A", {}, query_text=SAVINGS, scope="s1"))
    assert asyncio.run(fuzzy.search(v2, query_text=CHECKING, scope="s1"))["response"] == "A"
    assert asyncio.run(fuzzy.search(v2, query_text=CHECKING, scope="s2")) is None
    assert SemanticCache(cache_dir=str(tmp_path / "dflt")).exact_only is True


# ---- F1: every tier's hit shape goes through _call_ollama -----------------------------------------


def _seed(world, redis):
    """Store one answer through the real write path, with Redis either kept or discarded."""
    world.cache.redis = redis
    assert str(_ask(world.make(), SAVINGS)) == "fresh-1"


def test_semantic_tier_hit_through_call_ollama(world):
    _seed(world, NullRedis())  # vectors only; Redis never populated
    n = len(world.calls)
    out = _ask(world.make(), SAVINGS)
    assert str(out) == "fresh-1" and len(world.calls) == n


def test_redis_tier_hit_through_call_ollama(world):
    _seed(world, FakeRedis())
    _drop_local(world.cache)  # Redis alone
    n = len(world.calls)
    out = _ask(world.make(), SAVINGS)
    assert str(out) == "fresh-1" and len(world.calls) == n


def test_vault_tier_hit_through_call_ollama(world, tmp_path):
    vault = SimpleNamespace(
        get_experience_guidance=lambda q: {"guidance": "g", "relevant_context": [{"x": 1}]}
    )
    fuzzy = SemanticCache(cache_dir=str(tmp_path / "vz"), threshold=0.95, exact_only=False)
    fuzzy.redis, fuzzy._vault = FakeRedis(), vault
    n = len(world.calls)
    out = _ask(world.make(shared=fuzzy), "Tell me about tortoises")
    assert str(out).startswith("VAULT GUIDANCE:") and len(world.calls) == n


def test_vault_tier_is_not_served_in_exact_mode(world):
    world.cache._vault = SimpleNamespace(
        get_experience_guidance=lambda q: {"guidance": "g", "relevant_context": [{"x": 1}]}
    )
    n = len(world.calls)
    out = _ask(world.make(), "Tell me about tortoises")
    assert str(out) == "fresh-1" and len(world.calls) == n + 1


def test_file_tier_hit_through_call_ollama(world):
    agent = world.make()
    _ask(agent, SAVINGS)
    n = len(world.calls)
    out = _ask(agent, SAVINGS)  # same agent: its own file cache answers first
    assert str(out) == "fresh-1" and len(world.calls) == n
    assert out.embedding is not None and len(out.embedding) == 256


# ---- F3: a long OUTPUT keeps its embedding; cache identity stays strict -----------------------------


def test_long_output_keeps_its_embedding_while_cache_identity_stays_strict(
    world, monkeypatch, real_loader
):
    import cohezion.core.routing.router as router

    async def long_answer(*a, **k):
        return LONG_A  # beyond the stub encoder window (16 tokens)

    monkeypatch.setattr(router.LOCAL_ROUTER, "route_task", long_answer)
    agent = world.make()
    agent._encoder = CanonicalTextLatent(real_loader)
    assert agent._encoder.exceeds_token_limit(LONG_A)  # precondition: really past the window
    assert agent._semantic_vector(LONG_A) is None  # identity use: strict, unchanged
    out = _ask(agent, "short question")
    assert out.embedding is not None and len(out.embedding) == 256
