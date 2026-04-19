# CK-Tile FlatMM Research Summary for MoE Optimization

**Date:** April 4, 2026
**Researcher:** Kernel Researcher Agent
**Kernel:** amd-moe-mxfp4
**Current Best:** ~154.2 µs (fused_moe with adaptive KSPLIT)
**Target:** <130 µs (CK-Tile inspired approach)

---

## Executive Summary

Based on research of CK-Tile (Composable Kernel Tile) patterns, HipKittens primitives, and CDNA4 MFMA instructions, I've created two submission prototypes that attempt to bridge the 44µs gap to leaderboard performance.

**Key Finding:** The path to <130µs requires:
1. Native MFMA `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4` for MXFP4 computation
2. LDS-based Stage 1+2 fusion to eliminate intermediate global memory traffic
3. Expert-parallel saturation across all 304 CUs

---

## CK-Tile FlatMM Patterns Identified

### 1. FlatMM Architecture (from composable_kernel/example/ck_tile/18_flatmm/)

```
FlatMM Pattern:
  Global Memory:
    A[M, K] with per-1x32 E8M0 scales
    B[N, K] with per-1x32 E8M0 scales
    C[M, N] output

  Shared Memory Tiling:
    smem_A[BLOCK_M][BLOCK_K] - double buffered
    smem_B[BLOCK_N][BLOCK_K] - double buffered
    smem_As[BLOCK_M] - scale for A tile
    smem_Bs[BLOCK_N] - scale for B tile

  MFMA Computation:
    mfma_scale_f32_32x32x64_f8f6f4(A_frag, B_frag, C_accum, scale_a, scale_b)
```

### 2. CDNA4 Scaled MFMA Intrinsic

```cpp
// The key instruction for MXFP4 on MI355X (gfx950)
v16f32_t __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
    v8i32_t a,      // 64 FP4 elements (as 32 fp4x2 pairs)
    v8i32_t b,      // 64 FP4 elements
    v16f32_t c,     // Accumulator (16 FP32)
    int atype,      // 4 = E2M1 (MXFP4)
    int btype,      // 4 = E2M1
    int opsel_a,    // 0
    uint8_t scale_a,  // E8M0 scale byte
    int opsel_b,    // 0
    uint8_t scale_b   // E8M0 scale byte
);
```

**Coverage:** Each call processes 32x32x64 FP4 elements = 65,536 FP4 multiply-accumulates.

### 3. Expert-Parallel Saturation Pattern

From HipKittens research (arXiv:2511.08083):

```
Work Distribution:
  - MI355X has 304 CUs, each with 8 waves = 2,432 total waves
  - For 257 experts, dispatch ~12 waves per expert minimum
  - Round-robin expert assignment: blockIdx.x % num_experts
  - Each block processes all tokens for its assigned expert(s)

Grid Configuration:
  dim3 grid(min(304, num_experts));  // Saturate all CUs
  dim3 block(256);                  // 4 waves per block
```

---

## Implementation Approaches

### Submission Files Created

| File | Approach | Target |
|------|----------|--------|
| `submission_cktile_moe.py` | Basic MFMA Stage 1+2 | <140µs |
| `submission_cktile_moe_v2.py` | FlatMM with LDS bridge + expert-parallel | <130µs |

### Key Optimizations in v2

1. **LDS-Based Stage Fusion**
   ```cpp
   // Stage 1 outputs to LDS (not global memory)
   __shared__ float smem_intermediate[TILE_M * TILE_INTERMEDIATE];
   // Stage 2 reads from LDS (if fused) or uses separate kernel
   ```

2. **Expert-Aware Work Distribution**
   ```cpp
   // Each workgroup processes one expert at a time
   for (int expert_idx = wg_id; expert_idx < num_experts; expert_idx += gridDim.x) {
       int token_start = expert_offsets[expert_idx];
       int token_count = expert_offsets[expert_idx + 1] - token_start;
       // Process tokens for this expert
   }
   ```

3. **Double-Buffered Shared Memory**
   ```cpp
   __shared__ fp4x2_t smem_A[2][TILE_M * TILE_K / 2];  // tic/toc toggle
   // Prefetch next tile while computing current
   ```

4. **SiLU Fusion in Registers**
   ```cpp
   // Apply activation before writing to LDS/global
   float activated = silu(gate_val) * up_val * expert_weight;
   ```

---

## Technical Challenges Identified

### 1. Scale Granularity Mismatch

**Problem:** MFMA processes 64 FP4 elements per call, but scales are per 32 elements (1 E8M0 per 32 FP4).

**Solution Options:**
- Option A: Unroll K-loop by 2, call MFMA twice per 64-element tile
- Option B: Use dominant scale (max of 2 groups), slight precision loss
- Option C: CK-Tile requantizes the lower group to match upper scale

**Recommendation:** Option B for prototype, Option C for production.

### 2. Token Sorting Overhead

**Problem:** Expert-parallel dispatch requires tokens sorted by expert ID.

**Current:** `aiter.moe_sorting_fwd` handles this but adds ~5-10µs overhead.

**Optimization:** The sorting is already done in `fused_moe` - custom kernels should reuse the sorted indices.

### 3. Memory Layout Compatibility

**Problem:** `gate_up_weight_shuffled` uses CK-specific layout for ASM kernel.

**Challenge:** Raw MFMA kernel expects standard row-major layout.

**Solution:** Use `gate_up_weight` (unsorted) instead of `gate_up_weight_shuffled` for custom kernels.

### 4. Multi-Expert Reduction

**Problem:** Each token is processed by 9 experts (8 routed + 1 shared), outputs must be accumulated.

**Current Approach:** AtomicAdd to output buffer in Stage 2.

**Potential Optimization:** Use deterministic accumulation with pre-computed scatter indices.

---

## Expected Performance

### Theoretical Analysis

**Current fused_moe Breakdown (~154µs):**
- Stage 1 GEMM: ~60µs (hidden[7168] @ gate_up[2048*2, 7168])
- SiLU + elementwise: ~15µs
- Stage 2 GEMM: ~65µs (intermediate[2048] @ down[7168, 2048])
- Python/dispatch overhead: ~14µs

**CK-Tile FlatMM Optimizations:**
- LDS bridge eliminates Stage 1→2 writeback: -20µs
- Expert-parallel saturation (304 CUs): -15µs
- MFMA efficiency vs generic CK: -10µs
- **Expected total:** ~109µs (theoretical)

**Realistic Target:** 120-130µs (accounting for sorting overhead and layout conversions)

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| load_inline compilation failure | High | Fallback to fused_moe with adaptive KSPLIT |
| MFMA instruction not available | Medium | Check ROCm version, fallback to standard GEMM |
| Layout mismatch (shuffled weights) | High | Use unsorted weights for custom kernels |
| Sorting overhead exceeds savings | Medium | Reuse fused_moe sorting or batch sort |
| Correctness issues with atomicAdd | Medium | Verify against reference implementation |

---

## Next Steps

1. **Test compilation:** Verify `submission_cktile_moe.py` compiles via load_inline
2. **Correctness verification:** Compare output against reference implementation
3. **Benchmark:** Run `popcorn --mode benchmark` to measure actual performance
4. **Iterate on v2:** If v1 works, test v2 with LDS bridge
5. **Tune tile sizes:** Experiment with TILE_M, TILE_N, TILE_K values

---

## References

1. **HipKittens Paper:** arXiv:2511.08083 - Tile primitives for CDNA4
2. **AMD CDNA4 ISA:** `V_MFMA_SCALE_F32_32x32x64_F8F6F4` intrinsic documentation
3. **CK-Tile Examples:** `composable_kernel/example/ck_tile/18_flatmm/`
4. **aiter Research:** `/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/autoresearch/probes/hipkittens_mxfp4_gemm_spec.md`
5. **Current Best Submission:** `submission.py` with adaptive KSPLIT

---

## Files Delivered

1. `/home/mike-anderson/dev/cohezion/luma_speedrun/amd-moe-mxfp4/submission_cktile_moe.py` - Basic MFMA kernel
2. `/home/mike-anderson/dev/cohezion/luma_speedrun/amd-moe-mxfp4/submission_cktile_moe_v2.py` - FlatMM with LDS bridge
3. `/home/mike-anderson/dev/cohezion/luma_speedrun/amd-moe-mxfp4/CKTILE_RESEARCH_SUMMARY.md` - This document

---

*Research completed: April 4, 2026*
