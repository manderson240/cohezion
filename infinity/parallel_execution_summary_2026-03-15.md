# Luma AMD Speedrun - Parallel Execution Summary

## Date: 2026-03-15
## Status: All 3 kernels submitted to leaderboard

---

## Submissions Completed

### 1. GEMM (amd-mxfp4-mm)
- **Submission ID**: 561293 (v9), 561297 (tuned)
- **Status**: ✅ Done
- **Performance**: ~20-23 µs (best: 18.2 µs)
- **Approach**: HIP C++ quantization + aiter.gemm_a4w4_asm
- **Key Finding**: Using default configs, tuned configs don't exist for our shapes

### 2. MoE (amd-moe-mxfp4)
- **Submission ID**: 561303
- **Status**: ✅ Done
- **Approach**: aiter.fused_moe with KSPLIT=4
- **Code**: Standard submission with NT mode and adaptive KSPLIT

### 3. MLA (amd-mixed-mla)
- **Submission ID**: 561304
- **Status**: ✅ Done
- **Approach**: Direct torch.ops.aiter calls with three-regime routing
- **Code**: Phase 15 optimized with pre-allocated buffers

---

## Parallel Execution Results

### What Worked:
1. ✅ **Simultaneous submissions** - All 3 kernels submitted in parallel
2. ✅ **Absolute paths** - Required for popcorn-cli to find files
3. ✅ **Tuned configs created** - Shape-aware tile sizes for GEMM
4. ✅ **Pipeline operational** - Automated generation and submission working

### What Didn't Work:
1. ❌ **Helion on runner** - Not installed, need pure Triton extraction
2. ❌ **Tuned configs applied** - aiter doesn't use environment variables for configs
3. ❌ **Relative paths** - popcorn-cli requires absolute paths

---

## Performance Summary

| Kernel | Current | Target | Gap | Status |
|--------|---------|--------|-----|--------|
| GEMM | ~20 µs | ~10 µs | 2x | Submitted |
| MoE | ~155 µs | ~115 µs | 1.35x | Submitted |
| MLA | ~97 µs | ~54 µs | 1.8x | Submitted |

**Aggregate Points**: Pending leaderboard update

---

## Key Learnings from Parallel Execution

### 1. Submission Strategy
- **3 concurrent slots** available on runner
- **~3-4 minutes** per submission (JIT compilation dominates)
- **Absolute paths required** for popcorn-cli
- **No rate limits** - can submit freely

### 2. Optimization Opportunities
- **GEMM**: Create actual tuned configs in aiter's CSV files
- **MoE**: Try custom Triton kernel (aiter has ~50 µs overhead)
- **MLA**: Optimize regime thresholds based on profiling

### 3. Runner Environment
- **ROCm 7.1**, **PyTorch 2.10.0+rocm7.1**
- **aiter** with 1,314 pre-compiled kernels
- **No Helion** - must use pure Triton or aiter
- **Triton 3.6.0** available

---

## Files Created/Modified

### New Submissions:
- `submission_hip_v9_tuned.py` - GEMM with tuned configs
- `submission.py` (MoE) - Already existed, resubmitted
- `submission.py` (MLA) - Already existed, resubmitted

### Pipeline Scripts:
- `triton_submission_pipeline.py` - Automated submission pipeline
- `test_helion_output.py` - Helion testing
- `extract_triton.py` - Triton extraction utilities

### Documentation:
- `iteration_1_results.md` - Detailed results
- `HANDOFF.md` - Session handoff
- `gemm_success_2026-03-15.md` - GEMM success log

---

## Next Steps

### Immediate:
1. [ ] Check leaderboard rankings for all 3 kernels
2. [ ] Analyze submission logs for performance data
3. [ ] Compare against top performers

### Short-term:
1. [ ] Create actual tuned configs in aiter CSV format
2. [ ] Try fused quant+GEMM approach
3. [ ] Optimize MoE with custom Triton kernel

### Medium-term:
1. [ ] Analyze competitor submissions (John Hahn technique)
2. [ ] Implement winning patterns
3. [ ] Target Top 10 on all 3 kernels

---

## Resource Utilization

### Local (Framework Desktop):
- **CPU**: 16 cores used for parallel code generation
- **RAM**: ~6GB peak usage (safe)
- **Time**: ~30 minutes for full parallel execution

### Runner (MI355X):
- **Slots**: 3/3 utilized
- **Total time**: ~12 minutes (JIT compilation)
- **Success rate**: 3/3 submissions passed

---

## Conclusion

**Successfully executed parallel submission strategy**:
- All 3 kernels submitted simultaneously
- Pipeline operational and ready for iteration
- Clear optimization path identified (tuned configs)

**Blockers resolved**:
- Path issues fixed (use absolute paths)
- Submission process streamlined
- Error patterns documented

**Ready for next iteration** with:
1. Tuned config integration
2. Performance profiling
3. Competitor analysis

---

**Status**: Phase 1 complete, ready for optimization phase
**Confidence**: High (working submissions exist, clear path forward)
**Priority**: Create tuned configs for immediate performance gain
