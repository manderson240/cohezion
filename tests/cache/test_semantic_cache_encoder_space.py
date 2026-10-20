"""SemanticCache must never compare vectors across embedding spaces.

Defect (2026-09-22): the encoder was chosen by probing the :13305 router on
every put()/get(). A cache filled while the router was up (768D nomic) and then
queried while it was down (fallback tier) raised ``shapes not aligned`` in
``np.dot`` -- or, for two same-dim tiers, silently compared unrelated spaces.

All encoders here are fakes; nothing talks to the network.
"""

import asyncio
import hashlib

import numpy as np
import pytest

from cohezion.cache import semantic_cache as sc
from cohezion.cache.semantic_cache import SemanticCache


def _unit(dim: int, text: str) -> np.ndarray:
    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")
    v = np.random.default_rng(seed).standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


class _FakeLemonade:
    """768D encoder whose availability the test flips; counts probes."""

    def __init__(self) -> None:
        self.up = True
        self.probes = 0

    def is_available(self) -> bool:
        self.probes += 1
        return self.up

    def encode(self, text: str) -> np.ndarray:
        if not self.up:
            raise ConnectionError("router down")
        return _unit(768, text)


class _FakeTextEncoder:
    """384D fallback tier (a different space from the 768D one)."""

    def encode(self, text: str) -> np.ndarray:
        return _unit(384, text)


async def _noop_upsert(**_kw) -> None:
    return None


@pytest.fixture
def fake_lemonade(monkeypatch):
    fake = _FakeLemonade()
    monkeypatch.setattr(sc, "get_lemonade_encoder", lambda: fake)
    monkeypatch.setattr(sc, "get_text_encoder", lambda: _FakeTextEncoder())
    monkeypatch.setattr(sc, "_upsert_cache_entry", _noop_upsert)
    return fake


def _run(coro):
    return asyncio.run(coro)


def _router_drops(cache: SemanticCache, fake: _FakeLemonade) -> None:
    fake.up = False
    cache._lemonade_probe = None  # as if the probe TTL expired


def test_mismatched_space_query_is_a_miss_not_an_exception(fake_lemonade):
    cache = SemanticCache(similarity_threshold=0.5, enable_adaptive_threshold=False)
    _run(cache.put("what is a transformer", "attention"))
    assert cache.l2_cache

    _router_drops(cache, fake_lemonade)
    cache.l1_cache.clear()  # force the L2 (semantic) path
    assert _run(cache.get("what is a transformer")) is None
    assert cache.misses == 1


def test_same_space_get_still_hits(fake_lemonade):
    cache = SemanticCache(similarity_threshold=0.5, enable_adaptive_threshold=False)
    _run(cache.put("what is a transformer", "attention"))
    cache.l1_cache.clear()
    assert _run(cache.get("what is a transformer")) == "attention"
    assert cache.hits_l2 == 1


def test_mixed_space_put_does_not_corrupt_l2(fake_lemonade):
    cache = SemanticCache(similarity_threshold=0.5, enable_adaptive_threshold=False)
    _run(cache.put("alpha prompt", "A"))

    _router_drops(cache, fake_lemonade)
    _run(cache.put("beta prompt", "B"))  # 384D entry: must not raise in vstack

    fake_lemonade.up = True
    cache._lemonade_probe = None
    cache.l1_cache.clear()
    assert _run(cache.get("alpha prompt")) == "A"


def test_same_dim_different_encoder_is_not_compared(fake_lemonade, monkeypatch):
    """MiniLM and the SHA-256 hash tier are both 384D but unrelated spaces."""
    fake_lemonade.up = False
    cache = SemanticCache(similarity_threshold=-1.0, enable_adaptive_threshold=False)
    _run(cache.put("gamma prompt", "G"))  # sentence-transformers-384

    def boom():
        raise RuntimeError("encoder gone")

    monkeypatch.setattr(sc, "get_text_encoder", boom)
    monkeypatch.setattr(sc, "get_encoder", boom)
    cache.l1_cache.clear()
    # threshold -1: any cross-space dot product would register as a hit.
    assert _run(cache.get("gamma prompt")) is None


def test_router_probed_at_most_once_per_instance(fake_lemonade):
    cache = SemanticCache()  # default threshold -> construction also embeds
    for i in range(25):
        _run(cache.put(f"prompt {i}", f"resp {i}"))
        _run(cache.get(f"query {i}"))
    assert fake_lemonade.probes == 1
