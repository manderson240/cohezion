"""Run in a clean interpreter (no tests/conftest.py mocks): prints one JSON line."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))
from flume_latent_pairs import PARAPHRASE, UNRELATED

from cohezion.agents.base import BaseAgent
from cohezion.flume.canonical_latent import PARAPHRASE_THRESHOLD
from cohezion.flume.vae_encoder import get_encoder
from cohezion.reliability.semantic_cache import SemanticCache


enc = get_encoder()
if not enc.is_available():
    print(json.dumps({"unavailable": enc._error}))
    raise SystemExit(0)

GOLDEN_TEXT = "Restart the web server after the config change."
golden = [float(x) for x in enc.encode(GOLDEN_TEXT)[:8]]
exceeds = {
    "short": enc.exceeds_token_limit(GOLDEN_TEXT),
    "long": enc.exceeds_token_limit("word " * 300),
    "max_tokens": enc.max_tokens,
}

python_q = enc.encode("Explain what Python is")
python_cos = [float(python_q @ enc.encode(t)) for t in ("What is Python?", "Tell me about Python")]

# The original (un-mocked) body of tests/cache/test_semantic_embeddings.py::
# test_semantic_cache_hit_rate_improvement, run against the real cache class.
from cohezion.cache.semantic_cache import SemanticCache as L2Cache  # noqa: E402

_orig = L2Cache(similarity_threshold=0.85)


async def _orig_run():
    await _orig.put("What is Python?", "Python is a programming language")
    await _orig.put("Tell me about Python", "Python is an interpreted, high-level language")
    return await _orig.get("Explain what Python is")


_orig_result = asyncio.run(_orig_run())
original_body = {
    "result": _orig_result,
    "hits_l1": _orig.hits_l1,
    "hits_l2": _orig.hits_l2,
}

para = [float(enc.encode(a) @ enc.encode(b)) for a, b in PARAPHRASE]
unrel = [float(enc.encode(a) @ enc.encode(b)) for a, b in UNRELATED]
auc = float(np.mean([p > u for p in para for u in unrel]))

a, b = next((a, b) for a, b in PARAPHRASE if enc.encode(a) @ enc.encode(b) > 0.82)
unrelated = "What wine pairs well with grilled salmon?"

tmp = Path(tempfile.mkdtemp())
cache = SemanticCache(
    cache_dir=str(tmp / "sem"), threshold=PARAPHRASE_THRESHOLD, exact_only=False
)  # paraphrase serving is opt-in


async def _none(*_a, **_k):
    return None


cache.redis = SimpleNamespace(get=_none, set=_none)
cache._vault = SimpleNamespace(get_experience_guidance=lambda q: None)


class _Agent(BaseAgent):
    async def process(self, *a, **k):
        return None


agent = object.__new__(_Agent)
agent.model_name = "m"
agent.cache_dir = tmp
agent.config = SimpleNamespace(cache_ttl_seconds=3600)
agent._metrics = {"cache_hits": 0}
agent._semantic_cache = cache
agent._encoder = None  # BaseAgent resolves its own producer


async def run():
    await agent._set_cached(a, "RESPONSE-A")
    return await agent._get_cached(b), await agent._get_cached(unrelated)


hit, miss = asyncio.run(run())
print(
    json.dumps(
        {
            "auc_vs_unrelated": auc,
            "max_unrelated_cos": max(unrel),
            "hit": hit["response"] if hit else None,
            "miss": miss,
            "cache_hits": agent._metrics["cache_hits"],
            "stored_dim": int(cache.vectors[0].shape[0]),
            "query_dim": int(enc.encode(b).shape[0]),
            "paraphrase_cos": float(enc.encode(a) @ enc.encode(b)),
            "pair": [a, b],
            "golden": golden,
            "python_cos": python_cos,
            "original_body": original_body,
            "exceeds": exceeds,
        }
    )
)
