"""Canonical text latent: fixed width, real delegation, explicit unavailable state.

Each mechanism test fails if the mechanism is neutralized (see verification-depth.md):
restore a hash fallback in vae_encoder -> test_unavailable_raises_never_hash fails;
restore the random-init FlumeEncoder in agents/base.py -> test_base_agent_round_trip fails.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from cohezion.flume import vae_encoder
from cohezion.flume.canonical_latent import (
    LATENT_DIM,
    PARAPHRASE_THRESHOLD,
    CanonicalTextLatent,
    TextLatentUnavailable,
)


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))
from flume_latent_pairs import PARAPHRASE, UNRELATED  # noqa: E402


def _old_hash(text: str) -> np.ndarray:
    d = hashlib.sha256(text.encode()).digest()
    e = np.array([d[i % 32] / 255.0 for i in range(256)], dtype=np.float32)
    return e / np.linalg.norm(e)


def _stub_loader(dim: int, calls: list[str]):
    def loader():
        def embed(text: str) -> np.ndarray:
            calls.append(text)
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            return rng.standard_normal(dim).astype(np.float32)

        return embed

    return loader


def _raising_loader():
    raise OSError("model files missing")


@pytest.fixture(autouse=True)
def _reset():
    vae_encoder.reset_encoder()
    yield
    vae_encoder.reset_encoder()


@pytest.mark.parametrize("raw_dim", [384, 768])
def test_delegates_and_width_is_fixed(raw_dim):
    calls: list[str] = []
    enc = CanonicalTextLatent(_stub_loader(raw_dim, calls))
    z = enc.encode("restart the web server")
    assert len(calls) == 1  # the backend was really consulted
    assert z.shape == (LATENT_DIM,)  # width independent of the backend's native width
    assert abs(float(np.linalg.norm(z)) - 1.0) < 1e-5
    assert not np.allclose(z, _old_hash("restart the web server"))


def test_unavailable_raises_never_hash():
    enc = CanonicalTextLatent(_raising_loader)
    with pytest.raises(TextLatentUnavailable):
        enc.encode("anything")
    assert enc.encode_or_none("anything") is None
    assert enc.is_available() is False
    # the process-wide accessor behaves the same way
    vae_encoder._encoder_instance = vae_encoder.FlumeVAEEncoder(_raising_loader)
    with pytest.raises(TextLatentUnavailable):
        vae_encoder.get_encoder().encode("anything")


def test_zero_vector_is_unavailable_not_a_latent():
    enc = CanonicalTextLatent(lambda: lambda t: np.zeros(384, dtype=np.float32))
    with pytest.raises(TextLatentUnavailable):
        enc.encode("long input rejected by the server")


_LIVE = Path(__file__).with_name("_live_canonical_round_trip.py")


def _live() -> dict:
    """Un-mocked run in a clean interpreter (tests/conftest.py mocks sentence_transformers)."""
    out = subprocess.run(
        [sys.executable, str(_LIVE)],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    last = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not last.startswith("{"):
        pytest.fail(f"live round trip produced no result: {out.stderr[-600:]}")
    res = json.loads(last)
    if res.get("unavailable"):
        pytest.skip(f"MiniLM not loadable here: {res['unavailable']}")
    return res


def test_live_semantics_paraphrase_beats_unrelated():
    res = _live()
    assert res["auc_vs_unrelated"] >= 0.95  # measured 1.000; the hash control scores 0.51
    assert res["max_unrelated_cos"] < PARAPHRASE_THRESHOLD  # 0 unrelated false hits


def test_live_base_agent_round_trip_store_hit_miss():
    """Un-mocked: store under A, paraphrase hits, unrelated misses, dims equal."""
    res = _live()
    assert res["hit"] == "RESPONSE-A"
    assert res["cache_hits"] == 1
    assert res["miss"] is None
    assert res["stored_dim"] == res["query_dim"] == LATENT_DIM
    assert res["paraphrase_cos"] > PARAPHRASE_THRESHOLD


def _make_agent(tmp_path, encoder):
    from cohezion.agents.base import BaseAgent
    from cohezion.reliability.semantic_cache import SemanticCache

    cache = SemanticCache(cache_dir=str(tmp_path / "sem"), threshold=PARAPHRASE_THRESHOLD)

    async def _none(*a, **k):
        return None

    cache.redis = SimpleNamespace(get=_none, set=_none)
    cache._vault = SimpleNamespace(get_experience_guidance=lambda q: None)

    class _Agent(BaseAgent):
        async def process(self, *a, **k):  # pragma: no cover - abstract stub
            return None

    agent = object.__new__(_Agent)
    agent.model_name = "m"
    agent.cache_dir = tmp_path
    agent.config = SimpleNamespace(cache_ttl_seconds=3600)
    agent._metrics = {"cache_hits": 0}
    agent._semantic_cache = cache
    agent._encoder = encoder
    return agent


def _mapped_encoder(vectors: dict[str, np.ndarray]) -> CanonicalTextLatent:
    """Backend returning fixed raw vectors per text (near-equal pair, orthogonal unrelated)."""
    return CanonicalTextLatent(lambda: lambda t: vectors[t])


def test_base_agent_round_trip_with_mapped_vectors(tmp_path):
    base = np.zeros(384, dtype=np.float32)
    base[0] = 1.0
    near = base.copy()
    near[1] = 0.05
    far = np.zeros(384, dtype=np.float32)
    far[7] = 1.0
    enc = _mapped_encoder({"A": base, "A-paraphrase": near, "unrelated": far})
    agent = _make_agent(tmp_path, enc)

    async def run():
        await agent._set_cached("A", "RESPONSE-A")
        return await agent._get_cached("A-paraphrase"), await agent._get_cached("unrelated")

    hit, miss = asyncio.run(run())
    assert hit is not None and hit["response"] == "RESPONSE-A"
    assert agent._metrics["cache_hits"] == 1
    assert miss is None
    assert agent._semantic_cache.vectors[0].shape == enc.encode("A-paraphrase").shape


def test_base_agent_cache_is_noop_without_encoder(tmp_path):
    agent = _make_agent(tmp_path, CanonicalTextLatent(_raising_loader))

    async def run():
        await agent._set_cached("prompt A", "RESPONSE-A")
        return await agent._get_cached("a paraphrase of prompt A")

    assert asyncio.run(run()) is None
    assert agent._semantic_cache.vectors == []
    assert agent._metrics["cache_hits"] == 0


def test_stale_width_vectors_are_ignored_not_fatal(tmp_path):
    enc = CanonicalTextLatent(_stub_loader(384, []))
    agent = _make_agent(tmp_path, enc)
    agent._semantic_cache.vectors.append(np.ones(768, dtype=np.float32))  # old producer
    agent._semantic_cache.metadata.append({"response": "OLD"})
    assert asyncio.run(agent._get_cached("anything")) is None
