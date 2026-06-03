---
name: cohezion-semantic-cache-api
description: |
  Correct API and async patterns for cohezion SemanticCache. Use when:
  (1) cache.set() fails with AttributeError, (2) cache.get() always returns truthy even on miss,
  (3) measuring hit/miss rates gives wrong results, (4) writing SemanticCache integration tests.
  Key finding: .set() does NOT exist; .get() returns a coroutine when called without await.
  Verified: exp_JJJJ3, KKKK3 (autoresearch Rounds 12-14, 2026-05-27).
author: Claude Code (autoresearch Rounds 12-14)
version: 1.0.0
---

# Cohezion SemanticCache API

## Problem

Two silent failure modes when using SemanticCache:

1. `cache.set(key, value)` → `AttributeError: 'SemanticCache' object has no attribute 'set'`
2. `cache.get(key)` called without `await` returns a **truthy coroutine object**, not the cached value.
   All `cache.get(x) is not None` checks return `True` regardless of cache state.

## Correct API

```python
from cohezion.cache.semantic_cache import SemanticCache

cache = SemanticCache()

# Available methods: ['clear', 'get', 'get_stats', 'put']

# WRONG — AttributeError:
cache.set(key, value)

# RIGHT — write:
cache.put(key, value)

# WRONG — always truthy (coroutine object):
if cache.get(key) is not None:  # never misses!
    ...

# RIGHT — async-aware read:
import asyncio, inspect

result = cache.get(key)
if inspect.isawaitable(result):
    result = asyncio.run(result)
# or simply: asyncio.run(cache_get_async(key))
```

## Async Pattern (recommended)

```python
import asyncio, inspect
from cohezion.cache.semantic_cache import SemanticCache

async def demo():
    cache = SemanticCache()

    # Write
    await_if_needed = cache.put("prompt", "response")
    if inspect.isawaitable(await_if_needed):
        await await_if_needed

    # Read
    result = cache.get("same prompt")
    if inspect.isawaitable(result):
        result = await result

    return result  # "response" or None

asyncio.run(demo())
```

## Measured Hit Rates (exp_MMMM3, NNNN3, Round 14-15)

Threshold=0.85 (default):

| Query type | Hit rate |
|---|---|
| **Exact repeat** (L1 hash) | **100%** |
| **Paraphrase** (L2 cosine, similar meaning) | **50%** (2/4 pairs) |
| **Different topic** (L2 cosine, unrelated) | **100% miss** (0 false positives) |

Threshold exploration (0.70, 0.75, 0.80, 0.85): no threshold achieves ≥70% similar hits AND
≥70% different misses simultaneously. The 0.85 default is the best available tradeoff for precision.

**`SemanticCacheConfig(similarity_threshold=x)` may or may not propagate** depending on implementation
version — verify with `cache.get_stats()`.

## Claimed vs Verified

| Claim | Verified? | Notes |
|---|---|---|
| "95%+ hit rate" | Partially | True for exact-repeat queries (100%). Paraphrase hit rate is ~50%. |
| "L1 hash, L2 cosine, L3 vault" | Structure confirmed | L3 vault not tested in autoresearch |

## SemanticCache in Test Harness

```python
import asyncio
from cohezion.cache.semantic_cache import SemanticCache

def test_cache_discrimination():
    cache = SemanticCache()

    async def run():
        cache.put("seed prompt", "response")
        hit = await cache.get("similar prompt")
        miss = await cache.get("completely unrelated topic xyz")
        assert miss is None  # precision check
        return hit

    result = asyncio.run(run())
```

## References

- `src/cohezion/cache/semantic_cache.py` — implementation
- autoresearch.jsonl: exp_HHHH3 (Round 12, async bug), exp_JJJJ3 (Round 13, wrong API),
  exp_MMMM3 (Round 14, confirmed 50%/100%), exp_NNNN3 (Round 15, threshold tuning)
