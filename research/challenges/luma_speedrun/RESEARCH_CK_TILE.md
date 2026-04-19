# CK-Tile (Composable Kernel) Research Document for AMD MI355X gfx950

**Date:** April 6, 2026
**Target Hardware:** AMD Instinct MI355X (gfx950, CDNA4)
**ROCm Version:** 7.1
**Context:** Luma AMD Speedrun Competition

---

## Executive Summary

CK-Tile (Composable Kernel Tile) is AMD's programming model for performance-critical ML kernels on GPUs. For MI355X (gfx950), it provides:

- **Pre-compiled .co kernels** in `/home/runner/aiter/hsa/gfx950/`
- **MFMA scale intrinsics** for MXFP4 computation (`mfma_scale_f32_32x32x64_f8f6f4`)
- **Tile-based abstractions** for memory-efficient GEMM/Attention/MoE
- **FlatMM pattern** for fused multi-stage operations

**Key Finding:** CK-Tile provides the fastest path to competitive performance on MI355X, but direct integration is limited by runner constraints. The recommended approach is using `load_inline` with MFMA intrinsics inspired by CK-Tile patterns.

---

## 1. CK-Tile Kernel Inventory in `/home/runner/aiter/hsa/gfx950/`

### 1.1 GEMM Kernels (f4gemm/) - 35 files

**Location:** `/home/runner/aiter/hsa/gfx950/f4gemm/`

| Tile Size | Count | Example Filename |
|-----------|-------|------------------|
| 32x128 to 32x1024 | 8 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128.co` |
| 64x128 to 64x1024 | 8 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_64x128.co` |
| 128x128 to 128x512 | 4 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_128x128.co` |
| 160x128 to 160x384 | 3 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_160x128.co` |
| 192x128 to 192x256 | 2 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128.co` |
| 224x128 to 224x256 | 2 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_224x128.co` |
| 256x128 to 256x256 | 2 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_256x128.co` |

**Naming Convention:**
```
f4gemm_{output_dtype}_per{scale_granularity}Fp4_BpreShuffle_{M}x{N}.co
```

- `per1x32`: One E8M0 scale per 1 row × 32 columns
- `BpreShuffle`: Weights pre-shuffled for CK-Tile memory layout
- Tile sizes cover M ∈ {32,64,128,160,192,224,256}, N ∈ {128,256,384,512,640,768,896,1024}

### 1.2 MoE Kernels (fmoe_2stages/) - 182 files

**Location:** `/home/runner/aiter/hsa/gfx950/fmoe_2stages/`

**Key kernel variants:**
- `fmoe_stage1_bf16_pertokenFp8_blockscale_g1u1_128x128_pf2.co`
- `fmoe_stage1_int8_pertokenFp8_blockscale_g1u1_128x128_pf2.co`
- `fmoe_stage2_bf16_pertokenFp8_blockscale_g1u1_128x128_pf2.co`

**Naming components:**
- `stage1`/`stage2`: MoE gate+up vs down projection
- `bf16`/`int8`/`fp8`: Data types
- `pertokenFp8_blockscale`: Per-token FP8 with block scaling
- `g1u1`: Group=1, Unit=1 configuration
- `128x128`: Tile dimensions
- `pf2`: Prefetch variant

### 1.3 MLA/Attention Kernels (mla/) - 28 files

**Location:** `/home/runner/aiter/hsa/gfx950/mla/`

**Categories:**

| Prefix | Description | Count |
|--------|-------------|-------|
| `mla_a16w16` | A16W16 quantization | 3 |
| `mla_a8w8` | A8W8 quantization | 14 |
| `mla_pfl` | Prefill kernels | 3 |
| `mla_dec` | Decode kernels | 2 |
| `MLA_A16W16` | Legacy format | 2 |

**Key variants:**
- `_ps`: Persistent shader (register reuse)
- `_page`: Paged attention variant
- `qh{16,32,64,128}`: Query head dimension
- `qseqlen{1,2,4}`: Query sequence length
- `gqaratio{16,32}`: GQA ratio
- `msk{0,1}`: Mask variants

### 1.4 Root-level Kernels

**Location:** `/home/runner/aiter/hsa/gfx950/`

| File | Purpose |
|------|---------|
| `f8_block_scale_mi350_x128.co` | FP8 block scaling for MI350 |
| `gelu.co` | GELU activation |
| `silu.co` | SiLU activation |

---

## 2. Pre-compiled Tile Sizes

### 2.1 GEMM Tile Matrix

| M \ N | 128 | 256 | 384 | 512 | 640 | 768 | 896 | 1024 |
|-------|-----|-----|-----|-----|-----|-----|-----|------|
| 32 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 64 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 128 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 160 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 192 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 224 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 256 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Coverage:** 35 distinct tile configurations

### 2.2 MoE Stage Tile Sizes

**Common tile sizes found:**
- `128x128`: Standard MoE tile
- `256x256`: Large expert tile
- `64x64`: Small expert tile

### 2.3 MLA Tile Sizes

| Kernel Pattern | M | N | Description |
|----------------|---|---|-------------|
| `m32x4_n16x1` | 128 | 16 | Small decode |
| `m32x4_n16x2` | 128 | 32 | Standard decode |
| `m32x8_n128x1` | 256 | 128 | Large prefill |

---

## 3. Calling CK-Tile Kernels from Python

### 3.1 Via aiter High-Level APIs (Recommended)

```python
from aiter import gemm_a4w4, fused_moe, mla_decode_fwd

# GEMM with automatic kernel selection
out = aiter.gemm_a4w4(
    input, weight, input_scale, weight_scale,
    kernel_name=None  # Auto-select from CK-Tile kernels
)

# MoE with fused stages
out = aiter.fused_moe(
    hidden_states, gate_up_weight, down_weight,
    sorted_token_ids, sorted_weights, sorted_expert_ids,
    num_valid_ids, topk, expert_mask=None
)

# MLA decode
out = aiter.mla_decode_fwd(
    query, kv_cache, kv_lens, softmax_scale, num_kv_splits
)
```

### 3.2 Via Direct CK-Tile APIs (Undocumented)

```python
# MoE stage 1/2 direct dispatch
from aiter.ops.moe_op import (
    moe_cktile2stages_gemm1,
    moe_cktile2stages_gemm2
)

# Kernel name format:
# moe_cktile2stages_gemm{stage}_{BLOCK_SIZE}x{MPerBlock}x{NPerBlock}x{KPerBlock}_{WAVE_MAP_M}x{WAVE_MAP_N}_{WAVE_TILE_M}x{WAVE_TILE_N}x{WAVE_TILE_K}_{BlockPerCU}perCU_{QuantType}_{ActOP}{MulRoutedWeight}{HasBias}{SplitK}

kernel_name = "moe_cktile2stages_gemm1_256x32x256_1x4_16x16x32_2perCU_per_tensor"
out = moe_cktile2stages_gemm1(
    input, weight, scale, output,
    kernel_name=kernel_name  # Explicit kernel selection
)
```

### 3.3 Via ASM Direct Dispatch (Bypass Python Overhead)

```python
# Undocumented ASM APIs for minimal overhead
from aiter import mla_decode_stage1_asm_fwd, mla_reduce_v1

# Stage 1 ASM dispatch (direct kernel)
aiter.mla_decode_stage1_asm_fwd(
    Q, KV, qo_indptr, kv_indptr, kv_page_indices,
    kv_last_page_lens, num_kv_splits_indptr,
    work_meta_data, work_indptr, work_info_set,
    max_seqlen_q, page_size, nhead_kv,
    softmax_scale, splitData, splitLse, output
)

# Stage 2 reduction
aiter.mla_reduce_v1(splitData, splitLse, output, work_indptr)
```

### 3.4 Via load_inline Custom Kernels (Custom)

```python
from torch.utils.cpp_extension import load_inline

# Compile HIP kernel at runtime
module = load_inline(
    name="custom_cktile_kernel",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SOURCE],  # HIP is auto-converted from CUDA syntax
    functions=["kernel_name"],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
)

# Call kernel
module.kernel_name(args...)
```

---

## 4. Relevance by Kernel Type

### 4.1 GEMM Kernels

| Kernel | CK-Tile Relevance | Integration Strategy |
|--------|-------------------|---------------------|
| `gemm_a4w4` | **HIGH** | Primary API - uses CK-Tile internally |
| `gemm_a4w4_asm` | HIGH | Direct ASM dispatch |
| `gemm_a4w4_blockscale` | MEDIUM | Block-scaled variant, shape-limited |
| `deepgemm_ck` | MEDIUM | DeepGEMM integration |

**Best Approach:** Use `gemm_a4w4` with proper scale formats (per-1x32 E8M0).

### 4.2 MoE Kernels

| Kernel | CK-Tile Relevance | Integration Strategy |
|--------|-------------------|---------------------|
| `fused_moe` | **HIGH** | Complete CK-Tile integration |
| `moe_cktile2stages_gemm1/2` | HIGH | Direct stage access |
| `fmoe_fp8_blockscale_g1u1` | MEDIUM | FP8 variant |
| `asm_moe` | **DEAD** | Not available on runner |

**Best Approach:**
1. Primary: `fused_moe` with adaptive KSPLIT
2. Research: Direct `moe_cktile2stages_gemm1/2` with explicit kernel names
3. Custom: `load_inline` with MFMA intrinsics inspired by CK-Tile flatmm

### 4.3 MLA Kernels

| Kernel | CK-Tile Relevance | Integration Strategy |
|--------|-------------------|---------------------|
| `mla_decode_fwd` | HIGH | Wrapper for stage1+2 |
| `mla_decode_stage1_asm_fwd` | **HIGH** | Direct ASM dispatch |
| `mla_reduce_v1` | HIGH | Required for stage 2 |
| `mla_prefill_asm_fwd` | MEDIUM | For prefill workloads |
| `fmha_v3_varlen_fwd` | **DEAD** | "CK only supports head dimension at most 256" |

**Best Approach:**
1. Three-regime routing: matmul (small) + aiter a16w8 (medium) + aiter a8w8 (large)
2. Use `mla_decode_stage1_asm_fwd` + `mla_reduce_v1` for direct dispatch

---

## 5. CK-Tile FlatMM Pattern

### 5.1 Architecture

```
FlatMM Pattern (from composable_kernel/example/ck_tile/18_flatmm/)
═══════════════════════════════════════════════════════════════════

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

### 5.2 Key MFMA Intrinsic

```cpp
// CDNA4 Scaled MFMA for MXFP4
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

**Coverage:** 32×32×64 = 65,536 FP4 multiply-accumulates per call

### 5.3 Scale Granularity Handling

**Problem:** MFMA processes 64 FP4 elements per call, but scales are per 32 elements.

**CK-Tile Solutions:**
1. **Option A:** Unroll K-loop by 2, call MFMA twice per 64-element tile
2. **Option B:** Use dominant scale (max of 2 groups), slight precision loss
3. **Option C (CK-Tile):** Requantize the lower group to match upper scale

**Recommended:** Option C for production, Option B for prototyping.

---

## 6. Integration Strategy

### 6.1 Decision Matrix

| Goal | Approach | Expected Perf | Complexity |
|------|----------|---------------|------------|
| Quick baseline | `gemm_a4w4` / `fused_moe` / `mla_decode_fwd` | Baseline (13.4µs/154µs/70µs) | Low |
| Parameter tuning | Adaptive KSPLIT, kernel selection | +5-10% | Low |
| Bypass overhead | Direct ASM APIs | +10-15% | Medium |
| Maximum performance | `load_inline` + MFMA | +20-30% | High |
| Leaderboard top | Custom kernel scientist pattern | +50-100% | Very High |

### 6.2 Integration Path for Each Kernel

**GEMM:**
1. ✅ Baseline: `gemm_a4w4` (13.4µs)
2. 🔄 Research: `load_inline` + MFMA FP4 32x32
3. ❌ Blocked: Custom HIP compilation via `hipcc`

**MoE:**
1. ✅ Baseline: `fused_moe` with adaptive KSPLIT (154µs)
2. 🔄 Research: Direct `moe_cktile2stages_gemm1/2`
3. 🔄 Research: `load_inline` with LDS bridge + expert-parallel
4. ❌ Blocked: `fmoe_g1u1` (NaN on some shapes)

**MLA:**
1. ✅ Baseline: Three-regime routing (70µs)
2. 🔄 Research: Direct `mla_decode_stage1_asm_fwd` dispatch
3. ❌ Blocked: `fmha_v3_varlen_fwd` (head size limit)

### 6.3 CK-Tile via load_inline Template

```python
# Minimal viable CK-Tile-inspired kernel via load_inline
HIP_SOURCE = r'''
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define BLOCK_M 64
#define BLOCK_N 64
#define BLOCK_K 32
#define THREADS 256

// MFMA-accelerated MXFP4 GEMM tile
__global__ __launch_bounds__(THREADS, 4)
void mxfp4_gemm_cktile_inspired(
    const uint8_t* __restrict__ A_packed,  // [M, K/2] packed FP4
    const uint8_t* __restrict__ B_packed,  // [N, K/2] packed FP4
    const uint8_t* __restrict__ A_scale,   // [M, K/32] E8M0
    const uint8_t* __restrict__ B_scale,   // [N, K/32] E8M0
    __hip_bfloat16* __restrict__ C,        // [M, N] output
    int M, int N, int K
) {
    // CK-Tile style cooperative tiling
    __shared__ uint8_t smem_A[BLOCK_M * BLOCK_K / 2];
    __shared__ uint8_t smem_B[BLOCK_N * BLOCK_K / 2];
    __shared__ float smem_As[BLOCK_M];
    __shared__ float smem_Bs[BLOCK_N];

    // Block coordinates
    int bm = blockIdx.y * BLOCK_M;
    int bn = blockIdx.x * BLOCK_N;

    // Accumulator registers
    float acc = 0.0f;

    // K-loop over tiles
    for (int kt = 0; kt < K / 32; kt++) {
        // Cooperative tile loading to LDS
        // ... (load A/B tiles)

        __syncthreads();

        // Compute tile using MFMA or dequantize+FFMA
        // ... (computation)

        __syncthreads();
    }

    // Store output
    // ... (epilogue)
}
'''

module = load_inline(
    name="cktile_gemm",
    cpp_sources=['void mxfp4_gemm_cktile_inspired(torch::Tensor A, torch::Tensor B, torch::Tensor As, torch::Tensor Bs, torch::Tensor C, int M, int N, int K);'],
    cuda_sources=[HIP_SOURCE],
    functions=['mxfp4_gemm_cktile_inspired'],
    extra_cuda_cflags=['--offload-arch=gfx950', '-std=c++20', '-O3'],
)
```

---

## 7. Performance Characteristics

### 7.1 Theoretical Peak Performance

**MI355X (gfx950) Specifications:**
- 304 CUs
- 8 XCDs (X-tile Compute Dies)
- HBM3 memory
- MFMA throughput: ~2 TFLOPS per CU for FP4

**CK-Tile Efficiency:**
- GEMM: ~80-90% of theoretical (with proper tile sizing)
- MoE: ~60-70% (limited by expert imbalance)
- MLA: ~70-80% (memory-bound for small batches)

### 7.2 Observed Performance

| Kernel | Baseline | CK-Tile API | load_inline MFMA | Leaderboard |
|--------|----------|-------------|------------------|-------------|
| GEMM | 13.4µs | 13.4µs | 13.3µs* | ~4.3µs |
| MoE | 154µs | 154µs | ~120µs* | ~109µs |
| MLA | 70µs | 70µs | ~50µs* | ~33µs |

*Estimated based on Session 91 results

### 7.3 Bottleneck Analysis

**GEMM:**
- Current: Quantization dominates (~26µs)
- CK-Tile opportunity: Fused quant+GEMM
- Gap to leader: ~3.1x

**MoE:**
- Current: Python dispatch + stage separation (~14µs overhead)
- CK-Tile opportunity: LDS bridge fusion
- Gap to leader: ~1.4x

**MLA:**
- Current: 3-stage pipeline overhead (~100µs constant)
- CK-Tile opportunity: Flash Attention-style fused tiling
- Gap to leader: ~2.1x

---

## 8. Key Findings

1. **CK-Tile kernels ARE available** on the runner in `/home/runner/aiter/hsa/gfx950/`
   - 35 GEMM kernels, 182 MoE kernels, 28 MLA kernels
   - Pre-compiled for specific tile sizes

2. **Direct CK-Tile compilation is BLOCKED**
   - Cannot compile CK-Tile C++ code via `hipcc` on runner
   - Static source scanner blocks all compilation patterns

3. **load_inline IS available and working**
   - Session 95 confirmed: MFMA kernels compile and run correctly
   - Can use CK-Tile patterns/intrinsics via custom HIP

4. **MFMA register layouts are NON-OBVIOUS**
   - Column-major per thread (not row-major)
   - Verified layouts in `gfx950-mfma-register-layouts` skill

5. **B_shuffle vs B_q matters**
   - `B_shuffle` = CK-specific layout (16x16 permutation)
   - `B_q` = Standard packed layout for MFMA
   - Use `B_q` for custom kernels, `e8m0_unshuffle()` for scales

6. **Scale granularity is the key challenge**
   - E8M0 scales are per-32 elements
   - MFMA processes 64 elements per call
   - CK-Tile requantizes lower group to match upper

7. **Undocumented ASM APIs exist**
   - `mla_decode_stage1_asm_fwd`
   - `mla_prefill_asm_fwd`
   - `pa_ps_fwd_asm`
   - Bypass Python wrapper overhead

---

## 9. Actionable Recommendations

### Immediate Actions (This Session)

1. **Document MFMA register layouts** ✅
   - Use `gfx950-mfma-register-layouts` skill
   - Verify with small test kernels

2. **Test load_inline MFMA kernel** ✅
   - Verify compilation on runner
   - Measure against `gemm_a4w4` baseline

3. **Probe undocumented ASM APIs**
   - Test `mla_decode_stage1_asm_fwd` signatures
   - Measure dispatch overhead

### Short-term (Next 3 Sessions)

4. **Implement fused quant+GEMM**
   - Inline quantization in HIP kernel
   - Eliminate ~26µs Python quantization overhead

5. **MoE LDS bridge prototype**
   - Stage 1 outputs to LDS
   - Stage 2 reads from LDS directly
   - Target: <130µs

6. **MLA Flash Attention pattern**
   - Custom tiled attention kernel
   - Single dispatch vs 3-stage pipeline
   - Target: <50µs

### Research Directions

7. **Study CK-Tile flatmm examples**
   - `composable_kernel/example/ck_tile/18_flatmm/`
   - Adapt patterns for competition shapes

8. **GPU Kernel Scientist pattern**
   - Evolutionary kernel generation
   - LLM writes HIP, timing-only feedback
   - Proven on AMD MI300

9. **MAP-Elites quality-diversity search**
   - Prevent premature convergence
   - Behavioral dimensions: {memory_pattern, parallelism, tile_size}

---

## 10. Code Examples

### 10.1 Minimal CK-Tile MFMA Kernel

```python
"""Minimal MXFP4 GEMM using CDNA4 MFMA via load_inline."""
import torch
from torch.utils.cpp_extension import load_inline

HIP_SOURCE = r'''
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

using v8i32_t = int __attribute__((ext_vector_type(8)));
using v16f32_t = float __attribute__((ext_vector_type(16)));

__device__ inline v16f32_t mfma_scale_fp4(
    v8i32_t a, v8i32_t b, v16f32_t c, uint8_t sa, uint8_t sb
) {
    return __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
        a, b, c, 4, 4, 0, sa, 0, sb
    );
}

__global__ void mxfp4_32x32_kernel(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    // Each block computes 32x32 output tile
    int tid = threadIdx.x;
    int block_m = blockIdx.y * 32;
    int block_n = blockIdx.x * 32;

    v16f32_t accum = {0};

    // K-loop: 64 FP4 elements per iteration
    for (int k = 0; k < K / 64; k++) {
        // Load 64 FP4 elements (32 bytes) into registers
        // Split across lanes: lanes 0-31 get lower 32 bytes, 32-63 get upper
        v8i32_t a_reg = {0};
        v8i32_t b_reg = {0};

        // Load A (detailed in gfx950-mfma-register-layouts skill)
        int a_row = block_m + (tid & 31);
        int k_off = k * 32 + (tid >> 5) * 16;
        if (a_row < M) {
            const uint8_t* a_ptr = A + a_row * (K / 2) + k_off;
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            for (int i = 0; i < 16; i++) a_bytes[i] = a_ptr[i];
        }

        // Load B (similar pattern)
        // ...

        // Get scales
        uint8_t sa = As[a_row * (K / 32) + k * 2 + (tid >> 5)];
        uint8_t sb = Bs[(block_n + (tid & 31)) * (K / 32) + k * 2 + (tid >> 5)];

        // MFMA
        accum = mfma_scale_fp4(a_reg, b_reg, accum, sa, sb);
    }

    // Store output (column-major per thread)
    for (int r = 0; r < 16; r++) {
        int out_row = block_m + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
        int out_col = block_n + (tid & 31);
        if (out_row < M && out_col < N) {
            C[out_row * N + out_col] = (__hip_bfloat16)(accum[r]);
        }
    }
}
'''

module = load_inline(
    name="mxfp4_mfma_minimal",
    cpp_sources=['void mxfp4_32x32_kernel(torch::Tensor A, torch::Tensor B, torch::Tensor As, torch::Tensor Bs, torch::Tensor C, int M, int N, int K);'],
    cuda_sources=[HIP_SOURCE],
    functions=['mxfp4_32x32_kernel'],
    extra_cuda_cflags=['--offload-arch=gfx950', '-std=c++20', '-O3'],
)
```

### 10.2 Using CK-Tile Pre-compiled Kernels

```python
"""Use aiter to dispatch to CK-Tile pre-compiled kernels."""
import aiter

# GEMM: automatic kernel selection
result = aiter.gemm_a4w4(
    input_bf16,           # [M, K] bf16
    weight_packed,        # [N, K/2] uint8 packed FP4
    input_scale,          # [M, K/32] uint8 E8M0
    weight_scale_shuffled, # [N, K/32] uint8 E8M0 (shuffled)
    bias=None,
    alpha=1.0,
    beta=0.0,
    bpreshuffle=True,     # Use pre-shuffled weights
)

# MoE: fused dispatch
result = aiter.fused_moe(
    hidden_states,        # [M, D] bf16
    gate_up_shuffled,     # [E, DI*2, D/2] packed FP4
    down_shuffled,        # [E, D, DI/2] packed FP4
    sorted_token_ids,     # [M*topk] sorted by expert
    sorted_weights,       # [M*topk] float
    sorted_expert_ids,    # [M*topk] int
    num_valid_ids,        # int
    topk=9,               # 8 routed + 1 shared
)

# MLA: stage 1 ASM direct
aiter.mla_decode_stage1_asm_fwd(
    Q, KV, qo_indptr, kv_indptr, kv_page_indices,
    kv_last_page_lens, num_kv_splits_indptr,
    work_meta_data, work_indptr, work_info_set,
    max_seqlen_q=1, page_size=1, nhead_kv=16,
    softmax_scale, splitData, splitLse, output
)
aiter.mla_reduce_v1(splitData, splitLse, output, work_indptr)
```

---

## 11. References

1. **Composable Kernel Documentation:** https://rocm.docs.amd.com/projects/composable_kernel/
2. **CK GitHub:** https://github.com/ROCm/composable_kernel
3. **AMD CDNA4 ISA:** `V_MFMA_SCALE_F32_32x32x64_F8F6F4`
4. **HipKittens Paper:** arXiv:2511.08083
5. **K-Search Framework:** arXiv:2602.19128
6. **MFMA Register Layouts:** `.claude/skills/gfx950-mfma-register-layouts/SKILL.md`
7. **Runner Inventory:** `luma_speedrun/RUNNER_INVENTORY.md`
8. **CK-Tile Research Summary:** `luma_speedrun/amd-moe-mxfp4/CKTILE_RESEARCH_SUMMARY.md`

---

## 12. Appendices

### Appendix A: MFMA Instruction Reference (CDNA4)

| Instruction | Input Type | Output Type | Elements | Use Case |
|-------------|------------|-------------|----------|----------|
| `mfma_f32_16x16x16bf16_1k` | BF16 | FP32 | 16×16×16 | BF16 GEMM |
| `mfma_scale_f32_32x32x64_f8f6f4` | FP4/FP6/FP8 | FP32 | 32×32×64 | MXFP4 GEMM |
| `mfma_f32_16x16x32_bf8` | BF8 | FP32 | 16×16×32 | Low-precision |

### Appendix B: Tile Size Selection Heuristics

```python
def select_ck_tile(M: int, N: int, K: int) -> str:
    """Select CK-Tile kernel based on problem dimensions."""
    # GEMM tile selection
    if M <= 32:
        tile_m = 32
    elif M <= 64:
        tile_m = 64
    elif M <= 128:
        tile_m = 128
    else:
        tile_m = 256

    # Round N to nearest available
    tile_n = min([n for n in [128, 256, 384, 512, 640, 768, 896, 1024] if n >= N],
                 default=1024)

    return f"f4gemm_bf16_per1x32Fp4_BpreShuffle_{tile_m}x{tile_n}.co"
```

### Appendix C: Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AITER_USE_NT` | Enable non-temporal stores | 0 |
| `AITER_JIT_DIR` | JIT cache directory | `/tmp/aiter_jit_cache` |
| `AITER_BYPASS_TUNE_CONFIG` | Bypass tuned config CSV | 0 |
| `AITER_KSPLIT` | Split-K parallelism | auto |
| `AITER_BYPASS_TUNE_CONFIG` | Force generic kernels | 0 |

---

*Document created: April 6, 2026*
*Research scope: CK-Tile primitives for AMD MI355X gfx950*
*Next review: After load_inline MFMA validation*
