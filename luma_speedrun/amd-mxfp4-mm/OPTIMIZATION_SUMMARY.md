# AMD MXFP4 GEMM Optimization Summary

## Final Submission Status

**Submission File:** `submission.py`
**Configuration:** `aiter.gemm_a4w4_asm` with explicit 32x128 kernel selection
**Best Geomean:** ~23.1 µs (11% improvement over baseline ~24.5 µs)
**Leaderboard Submission:** Rate limited (1/hour), ready to submit

---

## Optimization Journey

### Attempted Approaches

| Approach | Geomean | M=16 Time | Status |
|----------|---------|-----------|--------|
| Baseline (`gemm_a4w4`) | 24.5 µs | 35.7 µs | Reference |
| AITER_KSPLIT=4 | 24.5 µs | 35.7 µs | ❌ No improvement |
| AITER_PERSISTENT_BO=1 | 24.5 µs | 35.7 µs | ❌ No improvement |
| **ASM + log2_k_split=0** | **23.1 µs** | **31.7 µs** | ✅ **Best** |
| ASM + log2_k_split=2 | 23.5 µs | 32.2 µs | ❌ Regression |
| Output buffer caching | 23.1 µs | 31.8 µs | ❌ No additional gain |
| torch.cuda._compile_kernel | N/A | N/A | ❌ ROCm unavailable |

### Key Finding

The **M=16,N=2112,K=7168** shape is the sole bottleneck:
- Aiter logs: `"not found tuned config in CKGEMM or asmGEMM, will use default config!"`
- Available kernels: 32x128, 192x128
- Missing: 16x128 (would be optimal for M=16)
- Using 32x128 kernel for M=16 wastes 50% of thread capacity

---

## Technical Details

### Best Configuration
```python
aiter.gemm_a4w4_asm(
    A_q_view, B_shuffle, A_scale_sh, B_scale_sh, out,
    "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E",
    bpreshuffle=True,
    log2_k_split=0  # Disables K-splitting for single-wave execution
)
```

### Why This Works
1. **Explicit kernel selection** bypasses auto-tuner fallback
2. **32x128 kernel** provides better occupancy than default for small M
3. **log2_k_split=0** avoids unnecessary K-dimension splitting overhead
4. **Pre-allocated output** eliminates allocation in hot path

---

## Results Persistence

**Local Storage:** `benchmark_results.jsonl`
**SurrealDB:** Connection failed (authentication required)
**Leaderboard:** Submission ready (rate limit: 1/hour)

---

## Path to <20 µs

**Current Gap:** ~3.1 µs to reach <20 µs target

**Potential Solutions:**
1. ✅ **Already achieved:** 11% improvement via ASM kernel selection
2. ⏳ **Requires upstream:** aiter adding tuned 16x128 kernel config
3. ⏳ **Requires policy change:** Unblocking `load_inline` for custom kernels
4. ❌ **Not feasible:** torch.cuda._compile_kernel doesn't exist in ROCm

---

## Files Modified

- `submission.py` - Optimized with ASM kernel selection
- `benchmark_results.jsonl` - All benchmark results
- `OPTIMIZATION_SUMMARY.md` - This summary

## Testing Compliance

✅ Every kernel change tested via `popcorn --mode test`
✅ All 4/4 correctness tests passing
✅ Benchmark runs completed successfully
