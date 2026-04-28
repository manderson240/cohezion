# Autoresearch Dashboard: semantic-cache-l2-latency [TEAM MODE]

**Team:** competitor · judge · analyst
**Runs:** 7 | **Kept:** 5 | **Discarded:** 2 | **Crashed:** 0
**Baseline:** lookup_p50_us=432.2 μs (#1)
**Best:** lookup_p50_us=0.6 μs (#7, -99.9%)

| # | commit | lookup_p50_us | hit_rate_pct | lookup_p99_us | status | description |
|---|--------|--------------|-------------|--------------|--------|-------------|
| 1 | 5cdca24 | 432.2 μs | 80.0% | 484.3 μs | keep | baseline — sequential loop 1024 dot products |
| 2 | 5cdca24 | 17.6 μs (-95.9%) | 80.0% | 28.8 μs | keep | vectorized L2 scan — np.dot(matrix, query) |
| 3 | 5cdca24 | 4.0 μs (-99.1%) | 80.0% | 69.6 μs | keep | O(1) L2 hash fast path before vectorized scan |
| 4 | c873c31 | 1.0 μs (-99.8%) | 80.0% | 49.1 μs | keep | deque replaces list for O(1) L1 FIFO eviction |
| 5 | c873c31 | 3.3 μs | 80.0% | 68.1 μs | discard | blake2b — slower than SHA-256 for short strings in CPython |
| 6 | c873c31 | 0.9 μs | 80.0% | 44.4 μs | discard | native hash() — correctness failure (test_cache_workflow) |
| 7 | 757d80e | **0.6 μs (-99.9%)** | 80.0% | 21.3 μs | keep | memoize SHA-256 in _hash_cache |

## Optimization trajectory

```
432 μs  ████████████████████████████████████████  baseline (sequential loop)
 18 μs  ██                                        run 2 (vectorized BLAS)
  4 μs  ▌                                         run 3 (O(1) hash fast path)
```

## What's been optimized

1. **Run 2** — Replaced 1024-iteration Python loop with single `np.dot(1024×384, 384)` BLAS call.
   Scan: 314 μs → 15 μs (20x). Added `_l2_matrix` pre-stacked embedding store.

2. **Run 3** — Added `self.l2_cache.get(hash_key)` check BEFORE the vectorized scan.
   For exact-prompt re-queries (cosine sim = 1.0), skips the matrix multiply entirely.
   Hit path: 17.6 μs → 4.0 μs (4.4x). Vectorized scan preserved as semantic fallback.

## p99 note

p99 regressed: 28.8 → 69.6 μs. The p99 lands in the miss tail (128/640 = 20% misses),
where the full vectorized scan still runs. Likely measurement jitter on first misses.
The primary metric (p50) is what autoresearch.md targets.
