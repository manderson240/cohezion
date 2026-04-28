# Autoresearch: SemanticCache put() Latency

## Objective

Reduce the latency of `put()` in `src/cohezion/cache/semantic_cache.py`.
The current implementation calls `np.vstack([self._l2_matrix, row])` on every
`_put_l2()` call when L2 is at capacity, which copies the entire 1024×384
float32 matrix (~1.5MB) on every insert. With a full L2 cache, every new `put()`
triggers this O(n) matrix copy.

Baseline: p50=332 μs per put() when L2 is full.

## Metrics

- **Primary**: `put_p50_us` (microseconds, lower is better)
- **Secondary**: `put_p99_us` (microseconds, lower is better)
- **Secondary**: `get_p50_us` (microseconds, lower is better — must not regress)

## How to Run

```bash
./autoresearch.sh
```

Outputs `METRIC name=number` lines. Runs in ~5 seconds.

## Files in Scope

- `src/cohezion/cache/semantic_cache.py` — focus on `_put_l2()`, `_put_l1()`, `put()`

## Off Limits

- `tests/` — do not modify tests
- Any file outside `src/cohezion/cache/`

## Constraints

- `uv run pytest tests/cache/ -q --tb=no -x --no-header --deselect tests/cache/test_semantic_embeddings.py::TestSemanticCacheDiscrimination::test_threshold_discrimination --deselect tests/cache/test_semantic_embeddings.py::TestSemanticTextEncoder --deselect tests/cache/test_cache_warmer_integration.py::TestCacheWarmerAnalyze::test_analyze_cache_effectiveness --deselect tests/cache/test_semantic_cache.py::TestSemanticCacheIntegration::test_cache_workflow` must pass
- `get_p50_us` must not regress beyond 1.0 μs (current best is 0.3 μs, allow up to 1.0 μs)
- No new pip dependencies — stdlib + numpy only

## What's Been Tried

_(updated as experiments accumulate)_

- Run 1 (baseline): np.vstack on every L2 insert when full — 332 μs p50.
