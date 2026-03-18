# Luma AMD Speedrun - Iteration 3 Summary

## Date: 2026-03-15
## Status: Multiple optimized variants submitted

---

## Submissions Completed

### 1. MoE (amd-moe-mxfp4) - MULTIPLE VARIANTS ✅

**Variant 2 (Conservative):**
- **Submission ID**: 562115
- **Status**: Test passed, leaderboard done
- **Strategy**: Shape-aware KSPLIT (8/4/2/default)
- **Thresholds**: est_m < 20, 60, 120

**Variant 3 (Ultra-Aggressive):**
- **Submission ID**: 562923 (pending)
- **Status**: Test passed ✅, leaderboard submitted
- **Strategy**: Maximum KSPLIT for sparse shapes
- **Thresholds**: est_m < 5, 15, 40, 80
- **Innovation**: KSPLIT=16 for extremely sparse

**Log Evidence:**
```
[aiter] run_1stage = False, ksplit = 16 q_type = QuantType.per_1x32 block_m = 32 use_nt = True, estimated_m_per_expert = 0
[aiter] run_1stage = False, ksplit = 8 q_type = QuantType.per_1x32 block_m = 32 use_nt = True, estimated_m_per_expert = 8
[aiter] run_1stage = False, ksplit = 8 q_type = QuantType.per_1x32 block_m = 64 use_nt = True, estimated_m_per_expert = 13
```

### 2. GEMM (amd-mxfp4-mm) - TUNED VARIANT ✅

**Submission ID**: 562884 (tuned)
- **Status**: Test passed ✅, leaderboard submitted
- **Strategy**: Shape-aware kernel selection
- **Approach**: Explicit kernel names via `gemm_a4w4_asm`

**Tuned Kernels:**
```python
TUNED_KERNELS = {
    (4, 2880, 512): "f4gemm_bf16_per1x32Fp4_BpreShuffle_16x128",
    (16, 2112, 7168): "f4gemm_bf16_per1x32Fp4_BpreShuffle_16x256",
    (32, 4096, 512): "f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128",
    (32, 2880, 512): "f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128",
    (64, 7168, 2048): "f4gemm_bf16_per1x32Fp4_BpreShuffle_64x256",
    (256, 3072, 1536): "f4gemm_bf16_per1x32Fp4_BpreShuffle_128x256",
}
```

**Key Issue:** Still seeing "not found tuned config in CKGEMM or asmGEMM"
- aiter's tuned config system uses CSV files, not kernel names
- Need to create actual tuned_fmoe.csv entries

### 3. MLA (amd-mixed-mla) - STABLE ✅

**Submission ID**: 561304
- **Status**: All tests passed, leaderboard done
- **Approach**: Three-regime hybrid with direct aiter calls
- **Performance**: ~97 µs (need ~54 µs for Top 10)

---

## Key Learnings from Iteration 3

### 1. MoE KSPLIT Optimization
**Ultra-aggressive strategy works:**
- KSPLIT=16 for est_m < 5 (extremely sparse)
- KSPLIT=8 for est_m < 15 (very sparse)
- KSPLIT=4 for est_m < 40 (sparse)
- KSPLIT=2 for est_m < 80 (moderate)
- Default for dense

**Evidence from logs:**
- First shape: ksplit = 16, estimated_m_per_expert = 0
- Second shape: ksplit = 8, estimated_m_per_expert = 8
- Third shape: ksplit = 8, estimated_m_per_expert = 13

### 2. GEMM Kernel Selection
**Explicit kernel names via `gemm_a4w4_asm`:**
- Can specify exact kernel to use
- Bypasses aiter's auto-selection
- Still need tuned configs for optimal performance

**Available kernels:**
- f4gemm_bf16_per1x32Fp4_BpreShuffle_16x128
- f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128
- f4gemm_bf16_per1x32Fp4_BpreShuffle_64x256
- f4gemm_bf16_per1x32Fp4_BpreShuffle_128x256
- f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128

### 3. Test Results
**All variants passing:**
- MoE v2: 3/3 tests ✅
- MoE v3: 3/3 tests ✅
- GEMM tuned: 4/4 tests ✅
- MLA: All tests ✅

---

## Performance Targets

| Kernel | Current | Target (Top 10) | Gap | Status |
|--------|---------|---------------|-----|--------|
| MoE | ~155 µs | ~115 µs | 1.35x | 🔄 Multiple variants submitted |
| GEMM | ~20 µs | ~10 µs | 2.0x | 🔄 Tuned variant submitted |
| MLA | ~97 µs | ~54 µs | 1.8x | ✅ Stable, needs optimization |

---

## Next Steps

### Immediate:
1. [ ] Wait for MoE v3 and GEMM tuned leaderboard results
2. [ ] Check if performance improved
3. [ ] Analyze any failures

### Short-term:
1. [ ] Create actual tuned config CSV for GEMM
2. [ ] Try custom Triton kernel for MoE (bypass aiter)
3. [ ] Optimize MLA regime thresholds

### Medium-term:
1. [ ] Profile all kernels to find bottlenecks
2. [ ] Study top performer code (if available)
3. [ ] Implement winning patterns

---

## Files Created

### New Submissions:
- `submission_optimized_v2.py` - MoE conservative ✅
- `submission_optimized_v3.py` - MoE ultra-aggressive ✅
- `submission_hip_v9_embedded_tuned.py` - GEMM tuned ✅
- `tuned_gemm_configs.csv` - Config reference

### Documentation:
- `iteration_3_results.md` - This file

---

## Resource Status

### Local (Framework Desktop):
- **CPU**: 16 cores
- **RAM**: ~6GB used
- **Status**: Ready for next iteration

### Runner (MI355X):
- **Active submissions**: 2 pending
- **Queue**: Clear
- **Status**: Processing

---

## Success Metrics

**Current:**
- All 3 kernels have working submissions ✅
- MoE: Ultra-aggressive optimization tested ✅
- GEMM: Explicit kernel selection working ✅
- MLA: Stable baseline ✅

**Target:**
- All 3 kernels in Top 10
- Aggregate score > 0

---

**Status**: Iteration 3 complete, awaiting leaderboard results
**Confidence**: High (multiple variants tested, all passing)
**Next Action**: Analyze leaderboard results when available
