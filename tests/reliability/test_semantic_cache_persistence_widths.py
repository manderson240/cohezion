"""reliability.SemanticCache persistence must survive vectors of mixed widths.

Before: np.array(self.vectors) over 768-d + 256-d entries is ragged, save() swallowed the
error, vectors.npy kept the old content and every new entry was lost on restart.
"""

import asyncio
import json
from types import SimpleNamespace

import numpy as np
import pytest

from cohezion.flume.canonical_latent import LATENT_DIM
from cohezion.reliability import semantic_cache as sc


@pytest.fixture(autouse=True)
def _no_redis(monkeypatch):
    async def _none(*a, **k):
        return None

    monkeypatch.setattr(sc, "get_redis", lambda: SimpleNamespace(get=_none, set=_none))


def _seed(d, widths):
    rng = np.random.default_rng(0)
    # an old producer wrote one matrix of a single width; mixed widths arise in memory/in a
    # later session, so seed the legacy file with the stale width only
    np.save(d / "vectors.npy", rng.standard_normal((len(widths), widths[0])).astype(np.float32))
    (d / "index.json").write_text(json.dumps([{"response": f"old{i}"} for i in range(len(widths))]))


def _unit(seed):
    v = np.random.default_rng(seed).standard_normal(LATENT_DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def test_stale_width_entries_are_purged_and_new_entries_survive_restart(tmp_path):
    _seed(tmp_path, [768, 768, 768])
    cache = sc.SemanticCache(cache_dir=str(tmp_path), threshold=0.8)
    assert cache.vectors == [] and cache.metadata == []  # purged in lockstep, not carried

    async def add_three():
        for i in range(3):
            await cache.add(_unit(i), f"new{i}", {}, query_text=f"q{i}")

    asyncio.run(add_three())
    restarted = sc.SemanticCache(cache_dir=str(tmp_path), threshold=0.8)
    assert [m["response"] for m in restarted.metadata] == ["new0", "new1", "new2"]
    assert len(restarted.vectors) == 3
    assert np.load(tmp_path / "vectors.npy").shape == (3, LATENT_DIM)
    assert len(json.loads((tmp_path / "index.json").read_text())) == 3


def test_save_is_width_safe_when_a_stale_vector_is_in_memory(tmp_path):
    cache = sc.SemanticCache(cache_dir=str(tmp_path), threshold=0.8)
    cache.vectors = [_unit(1), np.ones(768, dtype=np.float32), _unit(2)]
    cache.metadata = [{"response": "a"}, {"response": "stale"}, {"response": "b"}]
    cache.save()
    reloaded = sc.SemanticCache(cache_dir=str(tmp_path), threshold=0.8)
    assert [m["response"] for m in reloaded.metadata] == ["a", "b"]
    assert np.load(tmp_path / "vectors.npy").shape == (2, LATENT_DIM)


def test_add_rejects_wrong_width_visibly(tmp_path, caplog):
    cache = sc.SemanticCache(cache_dir=str(tmp_path), threshold=0.8)
    asyncio.run(cache.add(np.ones(768, dtype=np.float32), "x", {}))
    assert cache.vectors == [] and "add skipped" in caplog.text


def test_updating_an_existing_response_is_persisted(tmp_path):
    cache = sc.SemanticCache(cache_dir=str(tmp_path), threshold=0.8)
    asyncio.run(cache.add(_unit(1), "same", {}))
    asyncio.run(cache.add(_unit(2), "same", {}))
    assert np.allclose(np.load(tmp_path / "vectors.npy")[0], _unit(2))
