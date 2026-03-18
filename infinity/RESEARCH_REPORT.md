---
title: "Research Report: Luma AMD Speedrun Competition"
date: 2026-03-15
status: complete
tags: [infinity, gpu-optimization]
aspect: thinker
---

# Research Report: Luma AMD Speedrun Competition

**Date**: 2026-03-14
**Status**: Research Phase Complete
**Objective**: Understand winning strategies for Top 10 placement

## Executive Summary

**Critical Finding**: Competition explicitly blocks custom HIP/ASM kernels via static source scanning. Only approved methods work:
- ✅ Triton kernels (JIT compiled by Triton runtime)
- ✅ aiter library calls (pre-approved)
- ✅ torch operations (pre-approved)
- ❌ Custom HIP/ASM kernels (blocked)
- ❌ Runtime kernel compilation (blocked)
- ❌ Direct GPU memory manipulation (blocked)

## Current Rankings (manderson240)

| Kernel | Rank | Score | Top 10 | Gap |
|--------|------|-------|--------|-----|
| GEMM | 75/94 | 2.06e-05 (~20.6 µs) | ~1.07e-05 | 1.93x |
| MoE | 13/59 | 1.55e-04 (~155 µs) | ~1.52e-04 | 1.02x |
| MLA | 22/78 | 6.93e-05 (~69.3 µs) | ~5.41e-05 | 1.28x |

## Top Performer Analysis

### GEMM Leaders
1. **parcadei** (8.75 µs) - 1113 submissions
2. **John Hahn** (8.90 µs) - 721 submissions
3. **chineseman** (9.27 µs) - 153 submissions

**Pattern**: High submission counts suggest extensive tuning. Likely using:
- Triton with autotune
- Optimal tile sizes for each shape
- Fused operations

### MoE Leaders
1. **John Hahn** (114.61 µs) - 35 submissions ⭐
2. **champagnepapi** (114.66 µs) - 417 submissions
3. **josusanmartin** (141.35 µs) - 899 submissions

**Pattern**: John Hahn achieved rank 1 with only 35 submissions - suggests:
- Highly optimized approach
- Likely custom Triton kernel
- Efficient from the start

### MLA Leaders
1. **n8_gr8_** (4.33 µs) - 213 submissions
2. **Jayluci4** (4.37 µs) - 51 submissions
3. **g_structure** (4.38 µs) - 542 submissions

**Pattern**: Extremely fast times (4-5 µs) suggest:
- Custom FlashAttention implementation
- Optimized for decode (qseqlen=1)
- Possibly pre-compiled kernels (if allowed)

## Attempted Approaches (Local Analysis)

### 1. CUDA Graphs (submission_breakthrough_v1.py)
- **Approach**: Capture quant+GEMM in CUDA graph
- **Result**: No visible improvement
- **Issue**: Graph capture overhead, copy_() operations

### 2. Direct ASM Calls (submission_direct_asm.py)
- **Approach**: Call mla_decode_stage1_asm_fwd directly
- **Result**: Still ~69µs (rank 22)
- **Issue**: Python dispatch overhead remains

### 3. Custom HIP Kernels (submission_hiprtc_fused.py)
- **Approach**: Runtime compile HIP kernel with hiprtc
- **Result**: BLOCKED by competition
- **Issue**: Static source scanning rejects hipModuleLaunchKernel

### 4. Triton Kernels (submission_breakthrough_splitk_fp32.py)
- **Approach**: Custom Triton with split-K
- **Result**: ~24-37µs (slower than aiter)
- **Issue**: Triton dispatch overhead, not as optimized as aiter ASM

## Winning Strategy Hypothesis

Based on research, top performers likely use:

### GEMM (~8.75 µs)
- **Triton kernel** with optimal tile sizes
- **Autotune** for each shape (M,N,K)
- **Fused quant+GEMM** using tl.dot_scaled
- **Split-K** for small M shapes

### MoE (~114 µs)
- **Custom Triton kernel** replacing fused_moe
- **Fused token sorting + GEMM stages**
- **Optimal KSPLIT** per shape
- **Persistent kernel** across tiles

### MLA (~4.3 µs)
- **FlashAttention Triton kernel**
- **Fused Q@K^T + softmax + @V**
- **Optimized for qseqlen=1** (GEMV pattern)
- **Tiling strategy** for MLA dimensions

## Recommended Approach

Given constraints, focus on:

### Phase 1: MoE (Highest Probability)
**Target**: 155µs → 115µs (40µs improvement)
**Approach**: Custom Triton kernel
**Timeline**: 3-4 days
**Confidence**: 70%

### Phase 2: MLA (If MoE succeeds)
**Target**: 69µs → 54µs (15µs improvement)
**Approach**: FlashAttention Triton
**Timeline**: 2-3 days
**Confidence**: 60%

### Phase 3: GEMM (If time permits)
**Target**: 20.6µs → 10.7µs (10µs improvement)
**Approach**: Fused quant+GEMM Triton
**Timeline**: 3-4 days
**Confidence**: 50%

## Key Learnings

1. **Python API ceiling is real** - Can't beat ~155µs MoE with aiter.fused_moe
2. **Custom HIP blocked** - Competition security prevents runtime compilation
3. **Triton is the path** - Only way to write custom kernels that compile on runner
4. **Top performers use Triton** - John Hahn's 35 submissions vs our 100+ attempts
5. **Tile size matters** - Optimal BLOCK_M/N/K critical for performance
6. **Autotune essential** - Different shapes need different configs

## Next Steps

1. Write custom Triton MoE kernel
2. Use @triton.autotune for shape-specific optimization
3. Test on runner (JIT compilation allowed)
4. Profile and iterate
5. Scale to MLA/GEMM if successful

## Resources

- **Workspace**: /opencode_infinity/
- **Vault**: ~/vaults/cohezion-vault/infinity/
- **Submissions**: 64 MoE, 37 GEMM, 36 MLA variants tested
- **Time remaining**: 15 days

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Triton slower than aiter | Medium | Profile and optimize tile sizes |
| Compilation fails on runner | Low | Test in test mode first |
| Time runs out | Medium | Focus on MoE only |
| Top 10 not achieved | Medium | Accept rank 15-20 as partial win |

## Conclusion

**Custom HIP kernels are blocked**, but **Triton kernels are the viable path** to Top 10. Focus on MoE first (highest probability), then scale to other kernels. John Hahn achieved rank 1 with only 35 submissions - suggests efficient Triton approach exists.

**Recommendation**: Proceed with Triton-based MoE kernel development.

## Related
- [[competition_log|Competition Log]]
- [[CENTRAL_COMMAND|Central Command]]
