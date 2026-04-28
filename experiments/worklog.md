
## Put() Optimization — Campaign 2

### Run 1: baseline — put_p50_us=267.8 (KEEP)
- np.vstack on every _put_l2() when L2 full — copies entire 1024×384 float32 matrix per insert

### Run 2: pre-allocated ring buffer — put_p50_us=2.4 (KEEP, -99.1%)
- Timestamp: 2026-04-28
- What changed: Pre-allocated `_l2_matrix = np.zeros((max_l2_size, 384))` at `__init__`. `_put_l2()` now writes `_l2_matrix[_l2_write_idx] = embedding` directly (in-place, no allocation). Ring buffer pointer advances mod max_l2_size. FIFO eviction replaces LFU.
- Result: put_p50=2.4 μs, put_p99=20.0 μs, get_p50=0.2 μs
- Insight: np.vstack allocates a new (n+1)×384 array and copies ~1.5MB. In-place assignment copies only 1536 bytes (one row). 111× faster. 110/110 tests pass.
- Next: Profile what the remaining 2.4 μs is (SHA-256 hash? embedding copy? l2_cache dict?)

### Run 3: skip create_task when mcp_client=None — put_p50_us=1.6 (KEEP, -33%)
- Timestamp: 2026-04-28
- What changed: Added `if self.mcp_client:` guard before `asyncio.create_task(_vault_store)`. When no vault client is configured (default), skips task creation entirely instead of creating a task for a coroutine that immediately returns.
- Result: put_p50=1.6 μs, put_p99=2.6 μs, get_p50=0.2 μs
- Insight: asyncio.create_task has per-call overhead (~1 μs) even for instantly-completing coroutines. p99 dropped from 20.0→2.6 μs — tail was dominated by occasional slow task creation + scheduling.
- Next: Profile remaining 1.6 μs — likely SHA-256 (0.46 μs), CacheEntry dataclass (0.17 μs), _put_l1 dict ops (0.22 μs). Try pre-computing hash during put() via memoized cache.

### Run 4: remove dead l2_lfu_counts ops — put_p50_us=1.3 (KEEP, -19%)
- Timestamp: 2026-04-28
- What changed: l2_lfu_counts was only used for LFU eviction, replaced with FIFO in run 2. Removed `l2_lfu_counts.pop(old_key)` and `l2_lfu_counts[hash_key] = 1` from _put_l2(). Removed dead lfu increment from _promote_to_l1().
- Result: put_p50=1.3 μs, put_p99=2.0 μs, get_p50=0.2 μs
- Insight: Dead code that survived a structural refactor. 2 dict ops saved per put. SHA-256 hardware-accelerated (SHA-NI) so MD5 was slower — don't try alternative hashes.
- Next: CacheEntry @dataclass(slots=True) to reduce creation overhead; avoid timestamp=field(default_factory=time.time) if timestamp unused.
