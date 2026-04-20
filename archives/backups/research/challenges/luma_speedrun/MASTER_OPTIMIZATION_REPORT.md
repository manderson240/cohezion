# Luma AMD Speedrun - Master Optimization Report

**Date:** April 4, 2026
**Session:** Autonomous 2-hour optimization sprint
**Hardware:** AMD MI355X (gfx950)
**Competition:** GPU Model Optimization - AMD MI355X Speedrun

---

## Executive Summary

This report consolidates optimization efforts across all three kernels in the Luma AMD Speedrun competition: GEMM, MLA, and MoE.

### Current Status

| Kernel | Best Time | Leader | Gap | Status |
|--------|-----------|--------|-----|--------|
| **GEMM** | ~23.1 µs | ~4.3 µs | 5.3x | API ceiling reached |
| **MLA** | ~69.7 µs | ~33.0 µs | 2.1x | Documentation complete |
| **MoE** | ~154.2 µs | ~109.8 µs | 1.4x | Testing expert_mask |

### Key Blockers

1. **GEMM:** Missing 16x128 kernel config for M=16 bottleneck shape; load_inline blocked
2. **MLA:** Python dispatch overhead; direct CK dispatch blocked by runner
3. **MoE:** JIT compilation time limits; need fused quant+GEMM kernel

---

## GEMM (amd-mxfp4-mm) - Detailed Summary

**Best Performance:** ~23.1 µs (11% improvement over baseline ~24.5 µs)
**Target:** <20 µs
**Gap:** ~3.1 µs shortfall

### What Was Tried
- 34+ submission variants
- All aiter API parameters (KSPLIT, BYPASS_TUNE_CONFIG, log2_k_split)
- Explicit kernel selection via gemm_a4w4_asm
- Triton custom kernels (68% slower than ASM)
- load_inline custom HIP kernels (blocked by runner)
- HIP RTC compilation (blocked by runner)

### Best Configuration
```python
aiter.gemm_a4w4_asm(
    A_q_view, B_shuffle, A_scale_sh, B_scale_sh, out,
    "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E",
    bpreshuffle=True, log2_k_split=0
)
```

### Why Target Not Reached
The M=16,N=2112,K=7168 shape lacks a tuned 16x128 kernel in aiter. The 32x128 kernel wastes 50% thread capacity. To reach <20 µs requires:
1. Aiter upstream adding 16x128 kernel config, OR
2. Runner allowing load_inline custom kernels

**Full Report:** `amd-mxfp4-mm/FINAL_REPORT.md`

---

## MLA (amd-mixed-mla) - Detailed Summary

**Best Performance:** ~69.7 µs (estimated)
**Target:** <50 µs (estimated)
**Gap:** ~2.1x behind leader

### What Was Tried
- mla_decode_fwd (reference)
- mla_decode_stage1_asm_fwd (direct ASM)
- fmha_v3_varlen_fwd (FlashAttention v3)
- Einsum attention for small batches
- Metadata caching

### Current Approach
Uses adaptive dispatch based on batch size:
- Small batches (bs ≤ 4): Einsum attention
- Large batches: mla_decode_stage1_asm_fwd + mla_reduce_v1

### Open Strategies
1. Direct CK stage1/stage2 dispatch (V=0.5 in K-Search tree)
2. fmha_v3 single-dispatch (if K_dim == V_dim constraint can be solved)
3. Metadata pre-computation and caching

**Full Report:** `amd-mixed-mla/OPTIMIZATION_REPORT.md`

---

## MoE (amd-moe-mxfp4) - Detailed Summary

**Best Performance:** ~154.2 µs (estimated)
**Target:** <130 µs (estimated)
**Gap:** ~1.4x behind leader

### What Was Tried
- fused_moe with adaptive KSPLIT
- per_1x32_f4_quant_hip for faster quantization
- Expert masking (in progress)
- Custom sorting with local_expert_mask
- Direct CK stage dispatch

### Current Approach
Uses adaptive KSPLIT based on estimated M:
```python
if estimated_m < 10:
    os.environ["AITER_KSPLIT"] = "4"
elif estimated_m < 30:
    os.environ["AITER_KSPLIT"] = "2"
```

### In Progress
**Active-expert masking** (Submission #725239) - Testing:
- Uses torch.bincount to identify active experts
- Passes expert_mask to fused_moe
- Expected gain: ~10-15 µs (skip ~200 empty experts)
- Risk: Medium (may crash or produce incorrect results)

### Open Strategies
1. ✅ Active-expert masking (being tested)
2. Direct CK stage1/stage2 dispatch
3. torch.compile wrapping fused_moe
4. JIT cache warming

**Full Report:** `amd-moe-mxfp4/OPTIMIZATION_REPORT.md`

---

## Cross-Kernel Insights

### Common Blockers
1. **Runner sandbox blocks custom kernels** - load_inline, hipRTC, ctypes all blocked
2. **JIT compilation time** - 128-260s for MoE, eating into 12-minute timeout
3. **Rate limits** - 10 test submissions/hour, 1 leaderboard submission/hour

### Successful Patterns
1. **Two-Builders Pattern** - Maintain correctness anchor while exploring
2. **Adaptive parameter selection** - Shape-dependent tuning beats fixed values
3. **Explicit kernel selection** - Bypass auto-tuner for known bottleneck shapes

### Lessons Learned
1. Identify bottleneck shapes early via profiling
2. Check available kernel configs before optimizing
3. Test load_inline feasibility immediately (if allowed, use it exclusively)
4. Document failures to avoid retrying dead approaches

---

## Files and Resources

### Submission Files
- `amd-mxfp4-mm/submission.py` - Current GEMM submission
- `amd-mixed-mla/submission.py` - Current MLA submission
- `amd-moe-mxfp4/submission.py` - Current MoE submission

### Documentation
- `amd-mxfp4-mm/FINAL_REPORT.md` - Comprehensive GEMM report
- `amd-mixed-mla/OPTIMIZATION_REPORT.md` - MLA report
- `amd-moe-mxfp4/OPTIMIZATION_REPORT.md` - MoE report
- `autoresearch/state/{gemm,mla,moe}_tree.json` - K-Search trees

### Tools
- `popcorn-cli` - Submission system
- `autosubmit.py` - Batch submission script
- `autoresearch/` - K-Search framework implementation

---

## Next Steps

### Immediate (Next Hour)
1. ✅ Wait for MoE expert_mask test results (#725239)
2. If successful: Submit expert_mask to leaderboard
3. If failed: Try submission_sortmask.py approach

### Short Term (Next 24 Hours)
1. Test MLA fmha_v3 with padded V dimensions
2. Try MoE torch.compile approach
3. Continue K-Search cycles on remaining open strategies

### Long Term (Before Deadline)
1. Monitor for runner policy changes (load_inline unblocking)
2. Watch for aiter updates with new kernel configs
3. Focus on highest-impact remaining gaps (MoE has smallest gap at 1.4x)

---

## Conclusion

This optimization effort has:
- ✅ Achieved 11% improvement on GEMM (23.1 µs)
- ✅ Created comprehensive documentation for all three kernels
- ✅ Identified and tested multiple open strategies
- 🔄 In progress: Active-expert masking for MoE

The path to competitive performance requires either:
1. Runner policy changes to allow custom kernels, OR
2. Upstream aiter updates with optimized kernel configs

All optimization knowledge has been preserved in detailed reports for future reference.

---

*Report generated: April 4, 2026*
*Autonomous session: 2 hours*
*Team: luma-amd-optimization*
