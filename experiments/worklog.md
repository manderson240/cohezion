
## Put() Optimization — Campaign 2

### Run 1: baseline — put_p50_us=267.8 (KEEP)
- np.vstack on every _put_l2() when L2 full — copies entire 1024×384 float32 matrix per insert

### Run 2: pre-allocated ring buffer — put_p50_us=2.4 (KEEP, -99.1%)
- Timestamp: 2026-04-28
- What changed: Pre-allocated `_l2_matrix = np.zeros((max_l2_size, 384))` at `__init__`. `_put_l2()` now writes `_l2_matrix[_l2_write_idx] = embedding` directly (in-place, no allocation). Ring buffer pointer advances mod max_l2_size. FIFO eviction replaces LFU.
- Result: put_p50=2.4 μs, put_p99=20.0 μs, get_p50=0.2 μs
- Insight: np.vstack allocates a new (n+1)×384 array and copies ~1.5MB. In-place assignment copies only 1536 bytes (one row). 111× faster. 110/110 tests pass.
- Next: Profile what the remaining 2.4 μs is (SHA-256 hash? embedding copy? l2_cache dict?)
