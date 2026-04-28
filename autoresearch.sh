#!/usr/bin/env bash
# autoresearch benchmark: SemanticCache put() latency
# Outputs: METRIC put_p50_us=N  METRIC put_p99_us=N  METRIC get_p50_us=N
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Fast syntax pre-check
uv run python -c "import ast, pathlib; ast.parse(pathlib.Path('src/cohezion/cache/semantic_cache.py').read_text())" 2>/dev/null \
  || { echo "SYNTAX ERROR in semantic_cache.py"; exit 1; }

uv run python - <<'PYEOF'
import asyncio, statistics, time, sys
import numpy as np

import cohezion.cache.semantic_cache as _mod

_embed_cache = {}
def _fast_embed(text):
    if text in _embed_cache:
        return _embed_cache[text]
    rng = np.random.RandomState(abs(hash(text)) % (2**31))
    v = rng.randn(384).astype(np.float32)
    _embed_cache[text] = v / np.linalg.norm(v)
    return _embed_cache[text]

_mod.SemanticCache._text_to_embedding = staticmethod(_fast_embed)
from cohezion.cache.semantic_cache import SemanticCache


async def run_benchmark():
    cache = SemanticCache(max_l1_size=512, max_l2_size=1024, mcp_client=None)

    # Fill to capacity: L1=512, L2=1024
    warm = [f"warm_{i:04d}" for i in range(1024)]
    for p in warm:
        _fast_embed(p)  # pre-warm embed cache
    for i, p in enumerate(warm):
        await cache.put(p, f"resp_{i}")

    # put() workload: new prompts that must evict + rebuild
    new_prompts = [f"new_put_{i:04d}" for i in range(200)]
    for p in new_prompts:
        _fast_embed(p)  # pre-warm embed cache

    # Benchmark put() — all trigger LFU eviction when L2 is full
    put_lats = []
    for p in new_prompts:
        t0 = time.perf_counter()
        await cache.put(p, "resp")
        t1 = time.perf_counter()
        put_lats.append((t1 - t0) * 1_000_000)

    # Benchmark get() — use tail of warm prompts (not evicted by new puts)
    get_queries = warm[824:]  # indices 824-1023, still in L2 after 200 evictions
    for p in get_queries:
        _fast_embed(p)  # pre-warm all
    get_lats = []
    for p in get_queries[:200]:
        t0 = time.perf_counter()
        await cache.get(p)
        t1 = time.perf_counter()
        get_lats.append((t1 - t0) * 1_000_000)

    put_lats.sort()
    get_lats.sort()

    p50_put = statistics.median(put_lats)
    p99_put = put_lats[int(len(put_lats) * 0.99)]
    p50_get = statistics.median(get_lats)

    print(f"METRIC put_p50_us={p50_put:.1f}")
    print(f"METRIC put_p99_us={p99_put:.1f}")
    print(f"METRIC get_p50_us={p50_get:.1f}")

    print(f"[L2 size after: {len(cache.l2_cache)}]", file=sys.stderr)


asyncio.run(run_benchmark())
PYEOF
