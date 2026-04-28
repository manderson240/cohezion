# Autoresearch: SemanticCache put() Tail Latency (p99)

## Objective

Reduce **tail latency** of `put()` in `src/cohezion/cache/semantic_cache.py`.

Previous campaign (9 runs) reduced `put_p50_us` from 267.8 → ~1.0 μs via ring-buffer,
dead-code removal, SHA-256 elimination, and hot-path inlining.

The current `put_p99_us` is 1.9–3.0 μs with p50 ~1.0 μs — a 2–3× spread.
This variance signals periodic outliers from: dict resize events, memory allocation,
deque internal rebalancing, or numpy buffer cache misses.

Baseline: p99 ≈ 2.5 μs (fresh process, stable after warm-up).

## Metrics

- **Primary**: `put_p99_us` (microseconds, lower is better)
- **Secondary**: `put_p50_us` (microseconds, lower is better — must not regress beyond 1.5 μs)
- **Secondary**: `get_p50_us` (microseconds, lower is better — must not regress beyond 1.0 μs)

## How to Run

```bash
./autoresearch.sh
```

Outputs `METRIC name=number` lines. Runs in ~5 seconds.

## Files in Scope

- `src/cohezion/cache/semantic_cache.py` — focus on `put()`, `__init__`, `clear()`

## Off Limits

- `tests/` — do not modify tests
- Any file outside `src/cohezion/cache/`

## Constraints

- `uv run pytest tests/cache/ -q --tb=no -x --no-header --deselect tests/cache/test_semantic_embeddings.py::TestSemanticCacheDiscrimination::test_threshold_discrimination --deselect tests/cache/test_semantic_embeddings.py::TestSemanticTextEncoder --deselect tests/cache/test_cache_warmer_integration.py::TestCacheWarmerAnalyze::test_analyze_cache_effectiveness --deselect tests/cache/test_semantic_cache.py::TestSemanticCacheIntegration::test_cache_workflow` must pass
- `put_p50_us` must not regress beyond 1.5 μs
- `get_p50_us` must not regress beyond 1.0 μs
- No new pip dependencies — stdlib + numpy only

## What's Been Tried

_(updated as experiments accumulate)_

Previous campaign wins (transferred knowledge):
- Ring buffer pre-allocation (-99.1% p50)
- Skip asyncio.create_task when mcp_client=None
- Remove dead lfu_counts ops
- Eliminate SHA-256 hashing (use full_prompt string directly as key)
- Replace CacheEntry dataclass with plain str dicts
- Inline _put_l1/_put_l2 into put() hot path

## Experiment Ideas for p99 Reduction

1. **Pre-size l1_cache/l2_cache dicts**: `dict.__init__` with a capacity hint avoids
   resize events. Python dicts don't expose explicit pre-sizing, but creating with
   `{str(i): "" for i in range(max_size)}` then clearing pre-allocates the hash table.

2. **Pre-allocate deque with maxlen**: `deque(maxlen=max_l1_size)` auto-evicts without
   manual `popleft()` + `del l1_cache[...]` — reduces the L1 eviction path to one op.

3. **Avoid `in` membership test for l2_cache eviction**: `l2_cache.pop(old_key, None)`
   is one operation vs `if old_key and old_key in l2_cache: del l2_cache[old_key]`.

4. **Replace l2_cache dict with array-indexed storage**: Since `_l2_keys` already tracks
   which slot holds which key, `l2_cache` could be replaced by a parallel list `_l2_responses`
   indexed by slot. Eliminates hash-table ops entirely for L2 lookups.

5. **Numpy view for query scan**: `np.dot(self._l2_matrix[:fill_level], query)` scans
   only filled slots, reducing wasted computation when cache is not full.
