"""TTL edge cases of reliability.SemanticCache, each pinned against a surviving mutant."""

import asyncio
import json
from types import SimpleNamespace

import numpy as np
import pytest

from cohezion.flume.canonical_latent import LATENT_DIM
from cohezion.reliability import semantic_cache as sc


NOW = 1_800_000_000.0


class _Redis:
    def __init__(self):
        self.sets = []

    async def get(self, key):
        return None

    async def set(self, key, value, ttl=None):
        self.sets.append((key, value, ttl))


@pytest.fixture
def clock(monkeypatch):
    state = {"now": NOW}
    monkeypatch.setattr(sc, "time", SimpleNamespace(time=lambda: state["now"]))
    return state


@pytest.fixture
def redis(monkeypatch):
    r = _Redis()
    monkeypatch.setattr(sc, "get_redis", lambda: r)
    return r


def _vec():
    v = np.random.default_rng(3).standard_normal(LATENT_DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def _cache(tmp_path, ttl):
    return sc.SemanticCache(cache_dir=str(tmp_path), threshold=0.8, ttl_seconds=ttl)


def _search(cache):
    return asyncio.run(cache.search(_vec(), query_text="q", scope="s"))


def _add(cache, response="r", scope="s"):
    asyncio.run(cache.add(_vec(), response, {}, query_text="q", scope=scope))


# M2d: append path must stamp the real time, not 0
def test_fresh_append_is_served_and_stamped_with_now(tmp_path, clock, redis):
    cache = _cache(tmp_path, 3600)
    _add(cache)
    assert cache.metadata[0]["timestamp"] == NOW
    assert _search(cache)["response"] == "r"


# M2e: the update path must refresh the timestamp
def test_update_path_refreshes_the_timestamp(tmp_path, clock, redis):
    cache = _cache(tmp_path, 3600)
    _add(cache)
    clock["now"] = NOW + 3000
    _add(cache)  # same response/scope/query: update path
    assert len(cache.metadata) == 1 and cache.metadata[0]["timestamp"] == NOW + 3000
    clock["now"] = NOW + 6000  # past the ORIGINAL expiry, inside the refreshed one
    assert _search(cache)["response"] == "r"


# M2h: age exactly equal to ttl is expired, one second younger is served
def test_boundary_age_equal_to_ttl_is_expired(tmp_path, clock, redis):
    cache = _cache(tmp_path, 100)
    _add(cache)
    clock["now"] = NOW + 99
    assert _search(cache) is not None
    clock["now"] = NOW + 100
    assert _search(cache) is None


# M2f: the redis ttl is min(ttl, 24h), not a fixed 24h
@pytest.mark.parametrize(
    "ttl,expected", [(10, 10), (86400, 86400), (86401, 86400), (1e7, 86400), (None, 86400)]
)
def test_redis_ttl_is_the_smaller_of_ttl_and_24h(tmp_path, clock, redis, ttl, expected):
    _add(_cache(tmp_path, ttl))
    assert [t for _, _, t in redis.sets] == [expected]


# M2k: a non-numeric timestamp is expired, never a TypeError out of the lookup
@pytest.mark.parametrize("bad", ["123", str(NOW), None, [1], {"a": 1}])
def test_non_numeric_timestamp_is_expired_not_a_crash(tmp_path, clock, redis, bad):
    cache = _cache(tmp_path, 3600)
    _add(cache)
    cache.metadata[0]["timestamp"] = bad
    assert _search(cache) is None


# Finding 3: NaN, +-inf and future timestamps
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_timestamp_is_expired(tmp_path, clock, redis, bad):
    cache = _cache(tmp_path, 3600)
    _add(cache)
    cache.metadata[0]["timestamp"] = bad
    assert _search(cache) is None


def test_nan_timestamp_stays_expired_after_reload(tmp_path, clock, redis):
    cache = _cache(tmp_path, 3600)
    _add(cache)
    cache.metadata[0]["timestamp"] = float("nan")
    cache.save()
    assert json.loads((tmp_path / "index.json").read_text())[0]["timestamp"] != NOW
    assert _search(_cache(tmp_path, 3600)) is None


def test_future_timestamp_beyond_skew_is_expired_within_skew_is_served(tmp_path, clock, redis):
    cache = _cache(tmp_path, 3600)
    _add(cache)
    cache.metadata[0]["timestamp"] = NOW + 60  # within the stated 300 s tolerance
    assert _search(cache) is not None
    cache.metadata[0]["timestamp"] = NOW + 86400
    assert _search(cache) is None
    cache.metadata[0]["timestamp"] = NOW + 10 * 365 * 86400
    assert _search(cache) is None


def test_ttl_none_still_serves_everything(tmp_path, clock, redis):
    cache = _cache(tmp_path, None)
    _add(cache)
    cache.metadata[0]["timestamp"] = 0
    assert _search(cache) is not None


# The Redis tier has its own expiry check; a stale L1 row must not be served.
def test_redis_l1_serves_a_fresh_row_and_refuses_a_stale_one(tmp_path, clock, redis):
    cache = _cache(tmp_path, 3600)
    row = {"response": "L1", "scope": "s", "query_digest": sc.query_digest("q")}

    async def fresh(key):
        return {**row, "timestamp": NOW}

    redis.get = fresh
    assert _search(cache)["response"] == "L1"

    async def stale(key):
        return {**row, "timestamp": NOW - 7200}

    redis.get = stale
    assert _search(cache) is None
