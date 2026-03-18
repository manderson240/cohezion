# Luma AMD Speedrun - Iteration 2 Summary

## Date: 2026-03-15
## Status: Active optimization in progress

---

## Current Status

### 1. MoE (amd-moe-mxfp4) - OPTIMIZED ✅
- **Submission ID**: 562115 (v2)
- **Status**: Test passed, leaderboard submitted
- **Approach**: Shape-aware KSPLIT (8/4/2/default based on estimated_m)
- **Key Changes**:
  - KSPLIT=8 for very sparse (est_m < 20)
  - KSPLIT=4 for sparse (est_m < 60)
  - KSPLIT=2 for moderate (est_m < 120)
  - Default for dense (est_m >= 120)
  - doweight_stage1=False (correctness)

### 2. GEMM (amd-mxfp4-mm) - STABLE ✅
- **Submission ID**: 562116 (v9)
- **Status**: Test passed, already on leaderboard
- **Performance**: ~20-23 µs (best: 18.2 µs)
- **Key Issue**: "not found tuned config in CKGEMM or asmGEMM, will use default config!"
- **Next Step**: Need to create actual tuned configs in aiter's CSV format

### 3. MLA (amd-mixed-mla) - PENDING ⏳
- **Submission ID**: 561304
- **Status**: Submitted earlier, need to check results
- **Approach**: Three-regime hybrid with direct aiter calls

---

## Key Learnings from Iteration 2

### 1. MoE Optimization Success
**What worked:**
- Shape-aware KSPLIT selection based on estimated_m
- Conservative thresholds (20, 60, 120) vs aggressive (10, 50, 100)
- Keeping doweight_stage1=False for correctness

**What didn't work:**
- doweight_stage1=True caused test failures
- OPUS sorting didn't show clear benefit
- Block_m tuning via environment variables not effective

**Log evidence:**
```
[aiter] run_1stage = False, ksplit = 8 q_type = QuantType.per_1x32 block_m = 32 use_nt = True, estimated_m_per_expert = 0
[aiter] run_1stage = False, ksplit = 8 q_type = QuantType.per_1x32 block_m = 32 use_nt = True, estimated_m_per_expert = 8
[aiter] run_1stage = False, ksplit = 8 q_type = QuantType.per_1x32 block_m = 64 use_nt = True, estimated_m_per_expert = 13
```

### 2. GEMM Tuned Config Challenge
**Problem:** aiter doesn't use environment variables for tile sizes
**Evidence:** "not found tuned config in CKGEMM or asmGEMM, will use default config!"

**Solution path:**
- Need to create actual tuned config CSV files
- Location: `/home/runner/aiter/aiter/configs/tuned_fmoe.csv`
- Format: Shape-specific tile sizes

### 3. Submission Pipeline Working
- Parallel submissions operational
- Test mode validates before leaderboard
- ~3-4 minutes per submission
- Absolute paths required

---

## Performance Targets vs Current

| Kernel | Current | Target (Top 10) | Gap | Status |
|--------|---------|---------------|-----|--------|
| MoE | ~155 µs | ~115 µs | 1.35x | ✅ Optimized v2 submitted |
| GEMM | ~20 µs | ~10 µs | 2.0x | ⚠️ Need tuned configs |
| MLA | ~97 µs | ~54 µs | 1.8x | ⏳ Pending results |

---

## Next Iteration Plan

### Phase 1: Create Tuned Configs for GEMM (Priority 1)
**Goal:** Eliminate "not found tuned config" warning

**Steps:**
1. Analyze aiter's existing tuned config format
2. Create tuned_fmoe.csv entries for competition shapes
3. Submit and verify configs are loaded
4. Measure performance improvement

**Expected gain:** 20-30% improvement (from default to tuned)

### Phase 2: MLA Optimization (Priority 2)
**Goal:** Close gap to Top 10

**Current approach:** Three-regime hybrid
- Regime 1: einsum (bs <= 4 OR total_kv <= 65536)
- Regime 2: aiter a16w8 (total_kv <= 262144)
- Regime 3: aiter a8w8 (total_kv > 262144)

**Potential improvements:**
- Tune NUM_KV_SPLITS per batch size
- Try MXFP4 KV cache instead of FP8
- Optimize regime thresholds

### Phase 3: MoE Further Optimization (Priority 3)
**Goal:** Push into Top 10

**Current:** Shape-aware KSPLIT working
**Next:** 
- Try custom Triton kernel (bypass aiter overhead)
- Profile to find actual bottleneck
- Study mega-dmitriy's approach (Rank 1)

---

## Files Created/Modified

### New Submissions:
- `submission_optimized_v1.py` - MoE with doweight_stage1=True (FAILED)
- `submission_optimized_v2.py` - MoE with conservative KSPLIT (PASSED) ✅

### Documentation:
- `iteration_2_results.md` - This file
- Updated `HANDOFF.md`

---

## Critical Path to Top 10

### Immediate (Next 30 min):
1. [ ] Check MLA submission results
2. [ ] Create tuned config CSV for GEMM
3. [ ] Submit tuned GEMM variant

### Short-term (Next 2 hours):
1. [ ] Analyze tuned config impact on GEMM
2. [ ] Optimize MLA regime thresholds
3. [ ] Try custom Triton for MoE

### Medium-term (Today):
1. [ ] Profile all 3 kernels to find bottlenecks
2. [ ] Study top performer techniques
3. [ ] Implement winning patterns

---

## Resource Status

### Local (Framework Desktop):
- **CPU**: 16 cores available
- **RAM**: ~6GB used (safe)
- **Status**: Ready for next iteration

### Runner (MI355X):
- **Slots**: 0/3 currently active
- **Queue**: Clear for next submissions
- **Status**: Ready for parallel submissions

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tuned configs don't work | Medium | High | Fallback to current approach |
| MLA results poor | Medium | High | Focus on MoE/GEMM |
| Time runs out | Medium | High | Prioritize single kernel |
| Context window | Low | Medium | Use Ollama fallback |

---

## Success Metrics

**Current:**
- MoE: Test passing with optimized KSPLIT ✅
- GEMM: Stable ~20 µs performance ✅
- MLA: Submitted, awaiting results ⏳

**Target:**
- All 3 kernels in Top 10
- Aggregate score > 0

---

**Status**: Iteration 2 complete, ready for tuned config implementation
**Confidence**: High (MoE optimized, GEMM stable, MLA pending)
**Next Action**: Create tuned configs for GEMM
