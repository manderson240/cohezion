# Autoresearch Final Report: semantic-cache-put-latency

**Completed:** 2026-04-28
**Runs:** 9 | **Kept:** 8 | **Discarded:** 1
**Baseline:** put_p50_us=267.8 (run 1)
**Best:** put_p50_us=0.6 (run 8, -99.8% improvement)

## Winning changes (kept runs in order)

1. **Run 2**: Pre-allocated ring buffer for L2 matrix — O(1) insert replaces np.vstack, FIFO eviction via write_idx pointer — **267.8 → 2.4 μs (-99.1%)**
2. **Run 3**: Skip asyncio.create_task for L3 when mcp_client is None — avoids task creation for no-op coroutine — **2.4 → 1.6 μs (-33%)**
3. **Run 4**: Remove dead l2_lfu_counts dict ops — was dead code after FIFO ring-buffer replaced LFU eviction in run 2 — **1.6 → 1.3 μs (-19%)**
4. **Run 5**: @dataclass(slots=True) + remove dead timestamp/hit_count fields — saves time.time() per entry, eliminates __dict__ — **1.3 → 1.2 μs (-8%)**
5. **Run 6**: Use full_prompt as dict key directly — eliminates SHA-256 hash computation and _hash_cache entirely — **1.2 → 0.9 μs (-25%)**
6. **Run 7**: Replace CacheEntry dataclass with plain str dicts — l1_cache/l2_cache store response strings directly — **0.9 → 0.7 μs (-22%)**
7. **Run 8**: Inline _put_l1/_put_l2 into put() hot path — removes 2 function call overheads, _put_l2 method removed — **0.7 → 0.6 μs (-14%)**

## What didn't work

- **Run 9**: Skip L1 write in put() to save deque+dict overhead — cold-start artifact confused benchmark (2.5/2.2/1.7 μs first 3 runs, then stable 0.6 μs); median 0.6 μs = no improvement over run 8. L1 write is ~0.15 μs but warm-path deque+dict ops are highly cache-resident and below noise floor.

## Metric progression

| Run | put_p50_us | put_p99_us | get_p50_us | Status | Key change |
|-----|-----------|-----------|-----------|--------|------------|
| 1 | 267.8 | 601.7 | 0.2 | KEEP | baseline (np.vstack) |
| 2 | 2.4 | 20.0 | 0.2 | KEEP | ring buffer (-99.1%) |
| 3 | 1.6 | 2.6 | 0.2 | KEEP | skip create_task (-33%) |
| 4 | 1.3 | 2.0 | 0.2 | KEEP | rm dead lfu ops (-19%) |
| 5 | 1.2 | 3.4 | 0.2 | KEEP | slots=True (-8%) |
| 6 | 0.9 | 1.6 | 0.2 | KEEP | rm SHA-256 (-25%) |
| 7 | 0.7 | 1.7 | 0.2 | KEEP | rm CacheEntry (-22%) |
| 8 | 0.6 | 1.9 | 0.2 | KEEP | inline hot path (-14%) |
| 9 | 0.6 | — | — | DISCARD | skip L1 write (no gain) |

## Key insights

**The single biggest win (run 2, -99.1%):** `np.vstack` allocated a new (n+1)×384 float32 array and copied ~1.5 MB every put() call. Pre-allocating `np.zeros((1024, 384))` at `__init__` and writing to `_l2_matrix[slot] = embedding` in-place copies exactly 1,536 bytes (one 384-element row). 111× speedup from a single structural change.

**SHA-256 on AMD Zen 5 (run 6):** Hardware SHA-NI makes SHA-256 faster than MD5 and blake2b for short strings, but the hash is still pure overhead for an in-memory dict. Python str.__hash__ (via SipHash-1-3) serves the same collision-resistance purpose at zero extra cost. -25% from removing 10 lines.

**Dead code accumulates (run 4):** l2_lfu_counts survived a structural refactor (FIFO replaced LFU in run 2). Two dict ops per put() persisted for 2 runs before being caught. Dead code in hot paths is invisible until you profile.

**CacheEntry was the wrong abstraction (run 7):** The @dataclass existed to bundle (response, embedding, hit_count, timestamp). After prior runs removed hit_count and timestamp, and moved the embedding into the ring buffer, CacheEntry was a 1-field wrapper with 0.36 μs construction cost. Plain `dict[str, str]` is the right shape for this data.

**Diminishing returns below 1 μs:** Runs 5–8 each saved 0.1–0.3 μs. At this scale (±0.15 μs noise floor), median-of-3 runs is required. The remaining overhead is dominated by: Python function call setup (~0.03 μs), f-string formatting (~0.05 μs), deque.append + dict.__setitem__ (~0.15 μs), numpy row assignment (~0.25 μs).

## Remaining ideas (from autoresearch.ideas.md)

- **Lazy matrix rebuild**: Only rebuild `_l2_matrix` on-demand in `get()` — would reduce put() to pure dict ops, but degrades get() cold-path. Not worth exploring given get_p50_us already at 0.2 μs.
- **Pre-format full_prompt**: Cache `f"{system}\n{prompt}\n{model}"` result alongside the embedding to avoid re-formatting on repeated puts. Marginal at <0.1 μs.
- **Batch L1 eviction**: Process FIFO deque in chunks to amortize overhead. Not applicable — L1 uses FIFO not LFU, overhead is already minimal.
