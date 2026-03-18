# Luma AMD Speedrun - Final Iteration Summary

## Date: 2026-03-15
## Status: Multiple optimized variants tested

---

## Current Status

### 1. MoE (amd-moe-mxfp4) - PARTIAL SUCCESS ⚠️

**Variant 3 (Ultra-Aggressive):**
- **Submission ID**: 562923
- **Status**: Tests passed ✅, Benchmarks failed ❌
- **Issue**: KSPLIT=16 too aggressive for some shapes
- **Learning**: Need balance between sparse optimization and stability

**Working Variant 2:**
- **Submission ID**: 562115
- **Status**: All tests and benchmarks passed ✅
- **Strategy**: Conservative KSPLIT (8/4/2/default)
- **Performance**: Stable but not yet Top 10

### 2. GEMM (amd-mxfp4-mm) - CONFIG CHALLENGE ⚠️

**Tuned CSV Variant:**
- **Submission ID**: 563258
- **Status**: Tests passed ✅
- **Key Issue**: "not found tuned config in CKGEMM or asmGEMM, will use default config!"
- **Learning**: Environment variables don't work for aiter's tuned config system

**Root Cause:**
- aiter looks for tuned configs in `/home/runner/aiter/aiter/configs/tuned_fmoe.csv`
- Environment variables (AITER_BLOCK_M, etc.) are not used
- Need to actually create/modify the CSV file on the runner

### 3. MLA (amd-mixed-mla) - TYPE ERROR ❌

**Optimized Variant:**
- **Submission ID**: Multiple attempts
- **Status**: Type errors with KV data
- **Issue**: `mla_decode_stage1_asm_fwd` expects Tensor, not tuple
- **Learning**: KV data is (tensor, scale) tuple, need to extract tensor

---

## Key Learnings

### What Works:
1. ✅ **MoE with conservative KSPLIT** - Stable and passing
2. ✅ **GEMM with HIP quantization** - Fast and reliable
3. ✅ **MLA three-regime approach** - Good architecture

### What Doesn't Work:
1. ❌ **Ultra-aggressive KSPLIT** (16) - Causes benchmark failures
2. ❌ **Environment variables for tuned configs** - aiter ignores them
3. ❌ **Passing tuple to MLA kernel** - Needs plain tensor

### Critical Insights:
1. **aiter's tuned config system** uses CSV files, not env vars
2. **KSPLIT has limits** - Too high causes failures
3. **MLA KV data format** is (tensor, scale), not just tensor
4. **Shape-aware dispatch** is essential for performance

---

## Path to Top 10

### Immediate Actions Needed:

1. **GEMM**: Create actual tuned_fmoe.csv on runner
   - File location: `/home/runner/aiter/aiter/configs/tuned_fmoe.csv`
   - Format: M,N,K,BlockM,BlockN,BlockK,NumWarps,NumStages
   - Need write access to runner filesystem

2. **MoE**: Fine-tune KSPLIT thresholds
   - Current working: 8/4/2/default
   - Try: 6/3/2/default for better sparse performance
   - Monitor benchmark results

3. **MLA**: Fix KV data extraction
   - Change: `kv_data["fp8"]` to `kv_data["fp8"][0]`
   - Verify tensor shape matches kernel expectations

### Performance Gaps:

| Kernel | Current | Target | Gap | Priority |
|--------|---------|--------|-----|----------|
| MoE | ~155 µs | ~115 µs | 35% | High |
| GEMM | ~20 µs | ~10 µs | 50% | High |
| MLA | ~97 µs | ~54 µs | 44% | Medium |

---

## Files Created

### Working Submissions:
- `submission_optimized_v2.py` - MoE conservative ✅
- `submission_hip_v9.py` - GEMM stable ✅
- `submission.py` - MLA baseline ✅

### Experimental (Need Fixes):
- `submission_optimized_v3.py` - MoE too aggressive
- `submission_tuned_csv.py` - GEMM env vars ignored
- `submission_optimized_v2.py` - MLA type error

### Documentation:
- `iteration_1_results.md` - Initial pipeline
- `iteration_2_results.md` - Optimization attempts
- `iteration_3_results.md` - Ultra-aggressive tests
- `parallel_execution_summary.md` - Parallel strategy

---

## Resource Utilization

### Local (Framework Desktop):
- **CPU**: 16 cores used for code generation
- **RAM**: ~6GB peak usage
- **Time**: ~8 hours of development
- **Status**: Ready for continued iteration

### Runner (MI355X):
- **Submissions**: 20+ total
- **Success rate**: ~70% pass tests
- **Benchmark failures**: ~30% due to aggressive optimization
- **Queue**: Clear for next submissions

---

## Competition Status

### Current Rankings (Estimated):
- **MoE**: Middle of pack (~30th)
- **GEMM**: Lower middle (~60th)
- **MLA**: Lower middle (~40th)

### Aggregate Score: 0
Not in Top 10 for any kernel yet.

---

## Next Steps (Priority Order)

### 1. Fix GEMM Tuned Configs (Highest Impact)
- [ ] Create actual tuned_fmoe.csv on runner
- [ ] Verify configs are loaded (check logs)
- [ ] Measure performance improvement
- [ ] Submit to leaderboard

### 2. Fine-tune MoE KSPLIT (Medium Impact)
- [ ] Adjust thresholds: 6/3/2/default
- [ ] Test on all shapes
- [ ] Verify benchmarks pass
- [ ] Submit to leaderboard

### 3. Fix MLA Type Error (Medium Impact)
- [ ] Extract tensor from KV tuple
- [ ] Verify shape compatibility
- [ ] Test on all shapes
- [ ] Submit to leaderboard

### 4. Parallel Optimization (Ongoing)
- [ ] Continue submitting variants
- [ ] Monitor leaderboard rankings
- [ ] Iterate based on results

---

## Technical Debt

### Code Quality:
- Need to clean up experimental variants
- Consolidate working approaches
- Document winning patterns

### Testing:
- Need automated test validation
- Benchmark result tracking
- Performance regression detection

### Documentation:
- Update vault with final learnings
- Create handoff for future iterations
- Document aiter quirks and workarounds

---

## Conclusion

**Progress Made:**
- ✅ Working submissions for all 3 kernels
- ✅ Automated submission pipeline
- ✅ Shape-aware optimization strategies
- ✅ Error pattern analysis

**Remaining Work:**
- ⏳ Create actual tuned configs for GEMM
- ⏳ Fine-tune MoE thresholds
- ⏳ Fix MLA type issues
- ⏳ Reach Top 10 on all kernels

**Confidence Level:** Medium-High
- Clear path to improvement identified
- Technical blockers understood
- Multiple optimization strategies tested

**Time to Top 10:** Estimated 2-4 more iterations

---

**Status**: Foundation solid, need breakthrough optimizations
**Next Action**: Create tuned config CSV for GEMM
