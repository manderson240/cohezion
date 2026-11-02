# ruff: noqa: F811
"""File tier scope (B3) and TTL on every tier (B2), through the real BaseAgent._call_ollama.

Only the model call (router.LOCAL_ROUTER.route_task) is stubbed; it counts calls so "served from
cache" and "asked the model" are distinguishable. All agents share ONE file-cache directory, as
the default ``cache/swarm`` is shared by every agent in production.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from cohezion.reliability.semantic_cache import SemanticCache
from cohezion.swarm.swarm_types import SwarmConfig
from tests.agents.test_base_agent_cache_scope import (  # noqa: F401
    SAVINGS,
    AgentA,
    AgentB,
    FakeRedis,
    world,
)


def _agent(world, cls=AgentA, model="model-a", sem_dir=None, redis=None):
    """Agent on the shared file dir and a real SemanticCache (config TTL) with its own Redis."""
    agent = world.make(cls=cls, model=model)
    agent.cache_dir = world.tmp / "shared-files"
    agent.cache_dir.mkdir(exist_ok=True)
    cache = SemanticCache(
        cache_dir=str(sem_dir or world.tmp / "sem"),
        threshold=0.95,
        ttl_seconds=agent.config.cache_ttl_seconds,
    )
    cache.redis = redis or FakeRedis()
    agent._semantic_cache = cache
    return agent


def _ask(agent, prompt=SAVINGS, system="PIRATE", **kw):
    return asyncio.run(agent._call_ollama(prompt, system_prompt=system, **kw))


# ---- B3: the file tier is scoped ---------------------------------------------------------------


def test_same_scope_is_served_from_the_file_tier(world):
    _ask(_agent(world))
    n = len(world.calls)
    assert str(_ask(_agent(world))) == "fresh-1" and len(world.calls) == n


@pytest.mark.parametrize(
    "variant",
    [
        {"system": "LAWYER"},
        {"cls": AgentB},
        {"call_model": "other-model"},
    ],
    ids=["other-system-prompt", "other-agent-class", "per-call-model"],
)
def test_file_tier_never_serves_another_scope(world, variant):
    _ask(_agent(world))  # seeds "PIRATE" under model-a / AgentA
    n = len(world.calls)
    v = dict(variant)
    # fresh semantic dir + Redis: only the shared FILE directory can leak
    other = _agent(world, cls=v.pop("cls", AgentA), sem_dir=world.tmp / "sem2")
    kw = {"model": v.pop("call_model")} if "call_model" in v else {}
    out = _ask(other, **v, **kw)
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_file_key_uses_the_per_call_model(world):
    agent = _agent(world)
    assert agent._file_cache_key("p", None, agent._cache_scope("s", "m1")) != agent._file_cache_key(
        "p", None, agent._cache_scope("s", "m2")
    )


# ---- B2: an expired entry is never served from any tier ----------------------------------------


def _age(monkeypatch, seconds):
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + seconds)


def test_unexpired_entry_is_served_by_a_new_instance_control(world):
    _ask(_agent(world))
    n = len(world.calls)
    out = _ask(_agent(world, redis=FakeRedis()))  # same dirs, new instance, new Redis
    assert str(out) == "fresh-1" and len(world.calls) == n


def test_expired_entry_is_not_served_after_restart(world, monkeypatch):
    _ask(_agent(world))
    n = len(world.calls)
    _age(monkeypatch, 99999)  # cache_ttl_seconds is 3600
    fresh = _agent(world, redis=FakeRedis())
    out = _ask(fresh)
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


@pytest.mark.parametrize(
    "stamp",
    [float("inf"), float("nan"), time.time() + 1e9, True, "soon"],
    ids=["inf", "nan", "far-future", "bool", "non-numeric"],
)
def test_file_tier_expires_unusable_timestamps(world, stamp):
    """A forged or corrupt stamp must not outlive the TTL; same rule as the other tiers."""
    agent = _agent(world)
    _ask(agent)
    files = list(agent.cache_dir.glob("*.json"))
    assert files
    for path in files:
        path.write_text(json.dumps({**json.loads(path.read_text()), "timestamp": stamp}))
    n = len(world.calls)
    # fresh semantic dir + Redis: only the file tier could serve this
    out = _ask(_agent(world, sem_dir=world.tmp / "sem2"))
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_expired_local_vector_tier_alone_is_not_served(world, monkeypatch):
    """File tier removed, so only the persisted vector tier could answer."""
    _ask(_agent(world))
    for f in (world.tmp / "shared-files").glob("*.json"):
        f.unlink()
    n = len(world.calls)
    _age(monkeypatch, 99999)
    out = _ask(_agent(world, redis=FakeRedis()))
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_legacy_entry_without_timestamp_is_treated_as_expired(world):
    """Decision: an earlier version wrote no usable timestamp; with a TTL set it is expired."""
    _ask(_agent(world))
    for f in (world.tmp / "shared-files").glob("*.json"):
        f.unlink()
    index = world.tmp / "sem" / "index.json"
    meta = json.loads(index.read_text())
    for m in meta:
        m.pop("timestamp", None)
    index.write_text(json.dumps(meta))
    n = len(world.calls)
    out = _ask(_agent(world, redis=FakeRedis()))
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_expired_redis_entry_is_not_served(world, monkeypatch):
    agent = _agent(world)
    _ask(agent)
    redis = agent._semantic_cache.redis
    for f in (world.tmp / "shared-files").glob("*.json"):
        f.unlink()
    n = len(world.calls)
    _age(monkeypatch, 99999)
    # same Redis kept, local vectors dropped: only the Redis L1 entry could answer
    other = _agent(world, sem_dir=world.tmp / "sem3", redis=redis)
    out = _ask(other)
    assert str(out) != "fresh-1" and len(world.calls) == n + 1


def test_agent_passes_its_ttl_to_the_semantic_cache(tmp_path):
    real = AgentA(
        "model-a", config=SwarmConfig(mrp_sync=False, cache_ttl_seconds=123), cache_dir=tmp_path
    )
    assert real._semantic_cache.ttl_seconds == 123


def test_agents_own_semantic_cache_expires_entries(world, monkeypatch, tmp_path):
    """Consumption: the cache BaseAgent.__init__ constructs must itself carry the TTL."""
    from cohezion.reliability import semantic_cache as rel

    built = AgentA("model-a", config=SwarmConfig(mrp_sync=False), cache_dir=tmp_path / "files")
    assert isinstance(built._semantic_cache, rel.SemanticCache)
    built._semantic_cache.redis = FakeRedis()
    built._encoder = world.make()._encoder
    built.self_evaluate = world.make().self_evaluate
    _ask(built)
    n = len(world.calls)
    for f in (tmp_path / "files").glob("*.json"):
        f.unlink()  # only the persisted vector tier / Redis can answer
    _age(monkeypatch, 99999)
    again = AgentA("model-a", config=SwarmConfig(mrp_sync=False), cache_dir=tmp_path / "files")
    again._semantic_cache.redis = FakeRedis()
    again._encoder = built._encoder
    again.self_evaluate = built.self_evaluate
    assert str(_ask(again)) != "fresh-1" and len(world.calls) == n + 1


def test_downgraded_answer_is_stored_under_the_model_that_answered(world):
    agent = _agent(world)
    agent._credit_manager = type(
        "CM",
        (),
        {
            "can_afford": lambda self, a, m: False,
            "get_best_affordable_model": lambda self, a, m: "cheap-model",
        },
    )()
    _ask(agent)  # requested model-a, answered by cheap-model
    n = len(world.calls)
    plain = _agent(world, sem_dir=world.tmp / "sem2")  # model-a, affordable
    out = _ask(plain)
    assert str(out) != "fresh-1" and len(world.calls) == n + 1
