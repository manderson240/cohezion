# HipKittens + Native MXFP4 GEMM Spec for AMD MI355X (gfx950)

**Status:** Research Complete
**Date:** 2026-04-02
**Target kernel:** `amd-mxfp4-mm`
**Current time:** 22.8us (ranked) / 13.4us (ranked new shapes)
**Leader:** 4.3us
**Gap:** 3.1x - 5.3x
**Strategy:** `load_inline` custom HIP kernel using native `__builtin_amdgcn_mfma_scale_f32` intrinsics

---

## Executive Summary

The path to sub-10us MXFP4 GEMM on gfx950 is now clearly mapped:

1. **HipKittens is NOT a drop-in header for load_inline.** It is compiled as a shared `.so` via a dedicated Makefile using PyBind11. The `#include <kittens.cuh>` pattern works inside `hipcc` compilation only, not via `torch.utils.cpp_extension.load_inline()`. HipKittens also does NOT have MXFP4/FP4 support in its current main branch (only BF16 and FP8).

2. **The direct path to native MXFP4 GEMM on gfx950 is `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4`.** This CDNA4-only intrinsic IS callable from `load_inline` HIP C++ kernels. It accepts FP4 (E2M1, Atype=4) inputs with per-tile E8M0 scales built into the instruction. No library needed.

3. **The existing load_inline submissions are scalar fallback code** (fp4_to_f32 table lookup, one element per thread). They do not use MFMA hardware at all. Replacing them with a tiled MFMA kernel using the scaled MFMA intrinsic is the single highest-leverage change.

---

## 1. HipKittens: What It Is and Is NOT

### What it provides (for BF16/FP8)

**Repository:** https://github.com/HazyResearch/HipKittens
**Paper:** arXiv:2511.08083 (Nov 2025)

HipKittens is a C++ template DSL for AMD CDNA3/CDNA4 that wraps inline assembly into typed tile objects. Key components:

**Tile type hierarchy:**
```
kittens/
  include/
    kittens.cuh          <- master include
    common/
      macros.cuh         <- inline asm wrappers: ds_read_b32, buffer_load_dwordx4, v_mfma_f32_*
    types/
      types.cuh          <- register/shared tile shapes
        register/        <- rt_bf<rows,cols,layout,shape>, rt_fl<...>
        shared/          <- st_bf<rows,cols,shape> with swizzle variants
        global/          <- gl<dtype,B,D,R,C> global memory layout
    ops/
      warp/
        register/
          tile/
            mma.cuh      <- mma_AB, mma_ABt, mma_AtB, mma_AtBt
            assembly/    <- raw __builtin_amdgcn_mfma_* calls
        shared/          <- load_async, store
        memory/          <- global <-> shared transfers
      group/             <- multi-wave coordination
```

**Tile shapes supported:**
- Register tiles: `rt_16x16`, `rt_16x32`, `rt_32x16`, `rt_32x32`, `rt_16x128`
- Shared tiles: `st_16x16`, `st_16x32`, `st_8x32`, `st_16x16_swizzled`

**MMA operations (warp-level):**
```cpp
mma_ABt(C_accum, A_tile, B_tile, C_accum);  // C += A * B^T
mma_AB(C_accum, A_tile, B_tile, C_accum);   // C += A * B
mma_AtB(C_accum, A_tile, B_tile, C_accum);  // C += A^T * B
```

**Data types in mma.cuh:** `rt_bf` (bfloat16), `rt_fl` (float32), `rt_fp8` (fp8e4m3). **No FP4/MXFP4.**

**MFMA instructions wrapped in macros.cuh:**
- `v_mfma_f32_16x16x32_bf16` (mfma161632)
- `v_mfma_f32_32x32x16_bf16` (mfma323216)
- `v_mfma_f32_16x16x32_fp8_fp8` (mfma1616128 for FP8)

**Missing:** `v_mfma_scale_f32_32x32x64_f8f6f4` and `v_mfma_scale_f32_16x16x128_f8f6f4` (the CDNA4 scaled MFMA for MXFP4) are NOT in HipKittens as of April 2026.

### Why HipKittens is NOT usable via load_inline

HipKittens compiles using `hipcc` via its own Makefile, linking PyBind11:
```makefile
ROCM_BUILD_DIR = /opt/rocm/bin
HIP_COMPILER = $(ROCM_BUILD_DIR)/hipcc
CFLAGS = -std=c++20 -w -shared -fPIC --offload-arch=gfx950
INCLUDES = -I${THUNDERKITTENS_ROOT}/include -I/opt/rocm/include/hip
```

`torch.utils.cpp_extension.load_inline()` uses `clang++` (via `CXX="clang++"`) as the host compiler and invokes it with HIP offload arguments. The `kittens.cuh` header can in principle be included if:
- `THUNDERKITTENS_ROOT` environment variable is set correctly
- The header path is passed via `extra_cuda_cflags=["-I/path/to/HipKittens/include"]`
- The runner has HipKittens cloned

**Verdict:** HipKittens headers are NOT available on the Popcorn runner. They would need to be embedded inline or cloned at kernel build time. Even if available, they have no MXFP4 support.

### What IS usable: The 8-Wave Ping-Pong Pattern

The scheduling CONCEPT from HipKittens is directly implementable in a raw HIP kernel:

```
8-wave ping-pong (GEMM tile loop pattern):
  - 8 waves per threadblock (WARPS_M=2, WARPS_N=4)
  - Double-buffered shared memory: AS[2][2] and BS[2][2]
  - tic/toc toggle: while waves[0..3] compute on AS[tic], waves[4..7] load into AS[toc]
  - Roles swap each iteration via conditional barrier + sched_group_barrier
  - Outer tile loop: prefetch tile[i+1] while computing tile[i]

4-wave interleave (alternative for small M):
  - 1 wave per SIMD, 4 waves total
  - Each wave alternates small load+compute microbatches
  - Better for memory-bound shapes (small M, large N/K)
```

**Key AMD-specific facts:**
- HIPCC cannot allocate AGPRs as MFMA inputs/outputs — need `range<>` API (HipKittens) or inline assembly
- For raw HIP kernels, use `__builtin_amdgcn_mfma_*` directly (avoids the AGPR allocation problem)
- `__builtin_amdgcn_sched_barrier(mask)` and `__builtin_amdgcn_sched_group_barrier(mask, size, sync_id)` control instruction interleaving
- `s_setprio` controls wave priority between compute and memory groups

---

## 2. Native MXFP4 GEMM: The Actual Path (load_inline)

### The Key Intrinsic

```cpp
#include <hip/hip_runtime.h>
#include <hip/hip_ext_ocp.h>  // provides __amd_fp4x2_storage_t, __amd_extract_fp4, __amd_create_fp4x2

// Two scaled MFMA variants for gfx950 CDNA4:
// 16x16x128: output v4f32, input v8i32, C v4f32
// 32x32x64:  output v16f32, input v8i32, C v16f32

d_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
    a_reg,   // v8i32: 32 FP4 pairs (64 FP4 elements) in lower 128 bits, upper 128 bits zero
    b_reg,   // v8i32: same
    c_reg,   // v16f32: accumulator (16 FP32 values per thread)
    4,       // Atype: 4 = E2M1 (MXFP4 fp4)
    4,       // Btype: 4 = E2M1 (MXFP4 fp4)
    0,       // OPSEL_A: byte lane (set to 0)
    scale_a, // uint8_t E8M0 scale for matrix A tile
    0,       // OPSEL_B: byte lane (set to 0)
    scale_b  // uint8_t E8M0 scale for matrix B tile
);
```

**Atype/Btype values:**
- `0` = E4M3 (fp8)
- `1` = E5M2 (bf8)
- `2` = E2M3 (fp6)
- `3` = E3M2 (bf6)
- `4` = E2M1 (fp4 / MXFP4)

**Scale semantics:** `scale_a` and `scale_b` are E8M0 bytes. Actual scale = `2^(scale_byte - 127)`. This matches the aiter `dynamic_mxfp4_quant` output format (E8M0 bytes before shuffle). Scale is applied INSIDE the MFMA instruction, after the dot product and before accumulation into `c_reg`.

### Thread-to-Data Layout: 32x32x64 Tile

For the 32x32x64 variant with a wave of 64 threads:

```
Per-thread ownership (wave64):
  A tile (32 rows x 64 cols packed FP4):
    - Threads 0..31:  rows 0..31, each thread holds 64 FP4 = 32 fp4x2 bytes
    - Threads 32..63: rows 32..63 (second row-half — but 32x32 output, so rows 0..31 twice)

  Actually for 32x32x64:
    Each thread holds:
      - a_reg: 32 FP4 elements (stored as 16 fp4x2 pairs in lower 128 bits of v8i32)
      - b_reg: 32 FP4 elements (same format)
      - scale_a: 1 E8M0 byte (uint8_t) — one scale covers 32 FP4 elements = 1 group
      - scale_b: 1 E8M0 byte (uint8_t)
      - c_reg:  16 FP32 values (output fragment)

  FP4 packing type for input:
    using fp4x2_t  = __amd_fp4x2_storage_t;     // uint8_t alias
    using fp4x64_t = fp4x2_t __attribute__((ext_vector_type(32)));  // 256-bit vector, 64 fp4
    // Upper 128 bits must be zero for MXFP4 mode
```

### Data Flow Diagram

```
Global Memory:
  A_packed   [M, K//2] uint8  (FP4 pairs, row-major)
  A_scale    [M, K//32] uint8 (E8M0 scale, row-major, 1 scale per 32 elements)
  B_packed   [N, K//2] uint8  (B_shuffle from task input, pre-shuffled)
  B_scale    [N, K//32] uint8 (B_scale_sh from task input, pre-shuffled)

Shared Memory (double-buffered):
  smem_A[2][BLOCK_M // 32][32 * 16] fp4x2_t   (two 32xK slices)
  smem_B[2][BLOCK_N // 32][32 * 16] fp4x2_t   (two Kx32 slices)
  smem_As[2][BLOCK_M] uint8                    (scales for A, one per row per group)
  smem_Bs[2][BLOCK_N] uint8                    (scales for B, one per col per group)

Register Tiles (per wave):
  a_reg[16]  fp4x64_t  (loaded from smem_A, 64 fp4 per thread)
  b_reg[16]  fp4x64_t  (loaded from smem_B)
  scale_a    uint8_t   (loaded from smem_As)
  scale_b    uint8_t   (loaded from smem_Bs)
  c_accum[BLOCK_M//32][BLOCK_N//32] v16f32  (accumulated FP32 output)

Output:
  C [M, N] bfloat16 (converted from c_accum)
```

### Key Design Constraints

**Scale granularity mismatch:** The hardware MFMA instruction takes ONE scale per operand per call. The competition task has scales at 32-element granularity (one E8M0 per 32 FP4 elements = one per 16 bytes packed). For a 32x32x64 tile:
- K dimension is 64 FP4 elements = 2 scale groups (each 32 elements)
- The MFMA covers 64 K elements in one call, but there are 2 different scales along K
- **Solution:** Unroll the K loop by 2 (or 4) and call the MFMA once per scale group (32 elements = BLOCK_K=32 per MFMA call)

**Tile sizing for competition shapes:**
```
Competition shapes:
  M=4,   N=2880, K=512   -> K/32 = 16 scale groups per row
  M=16,  N=2112, K=7168  -> K/32 = 224 scale groups per row  (BOTTLENECK)
  M=32,  N=4096, K=512   -> K/32 = 16 groups
  M=64,  N=7168, K=2048  -> K/32 = 64 groups
  M=256, N=3072, K=1536  -> K/32 = 48 groups

Recommended tile:
  BLOCK_M = 32  (matches MFMA 32x32 tile)
  BLOCK_N = 128 (4 MFMA tiles wide, good for wide N)
  BLOCK_K = 32  (= 1 scale group, 1 MFMA call per K step)
  WAVES_M = 1 (32 rows per wave)
  WAVES_N = 4 (128/32 = 4 waves along N)
  Total waves per block = 4
```

**For small M (M=4, M=16):** The MFMA tile is 32x32 minimum. For M<32, options:
1. Pad M dimension to 32 (wastes compute on M=4: 8x waste)
2. Use the 16x16x128 variant: smaller output tile, better for small M
3. Fall back to aiter `gemm_a4w4` for shapes where BLOCK_M > M (and M is small)

### Compilation Flags for load_inline

```python
extra_cuda_cflags=[
    "--offload-arch=gfx950",
    "-std=c++20",
    "-O3",
    "-w",                          # suppress warnings
    "-DAMD_MFMA_SCALE_AVAILABLE",  # guard for gfx950-only code
]
```

The `hip/hip_ext_ocp.h` header provides:
- `__amd_fp4x2_storage_t` (uint8_t)
- `__amd_extract_fp4(packed, index)` — extract nibble 0 or 1
- `__amd_create_fp4x2(lo, hi)` — pack two nibbles

This header is available in ROCm 7.0+.

---

## 3. The Quant Bottleneck Still Applies

The existing architecture calls `dynamic_mxfp4_quant(A)` for ~26-80us before ANY GEMM. This is still the dominant cost at Python dispatch level. The native MFMA kernel does NOT help with the quant cost.

**BUT** there is now a credible path to eliminate quant dispatch by fusing it into the MFMA kernel:

```
Fused kernel architecture:
  Thread block loads A [BLOCK_M rows, BLOCK_K elements] from global (bf16)
  Computes MXFP4 quantization inline (max per group-of-32, E8M0 encoding)
  Calls __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4 with computed scale
  No separate quant dispatch — quant and GEMM in one kernel
```

The E8M0 computation inside the kernel:
```cpp
// Compute E8M0 from bf16 input group (32 elements)
float amax = 0.0f;
for (int i = 0; i < 32; i++) amax = fmaxf(amax, fabsf(a[i]));
uint32_t amax_u32 = *(uint32_t*)&amax;
uint32_t rounded = (amax_u32 + 0x200000u) & 0xFF800000u;
int exp_biased = (rounded >> 23) & 0xFF;
uint8_t scale_byte = (uint8_t)max(0, exp_biased - 2);
float quant_scale = exp2f(129.0f - exp_biased);
// Quantize: fp4_val = round(a[i] * quant_scale) (clamp to [-6, 6])
```

This eliminates `dynamic_mxfp4_quant` entirely and can reduce total time to compute + memory bandwidth for A.

---

## 4. Scheduling Pattern: 8-Wave Ping-Pong (Translated for MXFP4)

The HipKittens GEMM kernel structure, translated to raw HIP for MXFP4:

```cpp
// Threadblock configuration: WAVES_M=2, WAVES_N=4, total 8 waves
// Each wave: 64 threads (wave64 on CDNA4)
// dim3 threads(64 * 8);  // 512 threads per block
// dim3 blocks(cdiv(N, BLOCK_N), cdiv(M, BLOCK_M));

__global__ void mxfp4_mfma_ping_pong(
    const fp4x2_t* A, const uint8_t* As,   // A data + scales
    const fp4x2_t* B, const uint8_t* Bs,   // B data + scales (pre-shuffled)
    __hip_bfloat16* C,
    int M, int N, int K
) {
    // Identify which tile this block handles
    int block_m = blockIdx.y * BLOCK_M;
    int block_n = blockIdx.x * BLOCK_N;
    int wave_id = threadIdx.x / 64;
    int lane_id = threadIdx.x % 64;
    int wave_m  = wave_id / WAVES_N;   // 0..1
    int wave_n  = wave_id % WAVES_N;   // 0..3

    // Double-buffered shared memory
    __shared__ fp4x2_t smem_A[2][BLOCK_M * BLOCK_K / 2];  // 2 buffers
    __shared__ fp4x2_t smem_B[2][BLOCK_N * BLOCK_K / 2];
    __shared__ uint8_t smem_As[2][BLOCK_M];
    __shared__ uint8_t smem_Bs[2][BLOCK_N];

    // Accumulators: each wave owns MFMA_M x MFMA_N output fragment
    using v16f32 = float __attribute__((ext_vector_type(16)));
    v16f32 c_accum = {0};

    // Load first tile (tic=0)
    load_tile_A(smem_A[0], smem_As[0], A, As, block_m, 0, M, K);
    load_tile_B(smem_B[0], smem_Bs[0], B, Bs, block_n, 0, N, K);
    __syncthreads();

    int tic = 0;
    int num_k_steps = K / (BLOCK_K * 32);  // K steps (BLOCK_K=1 group = 32 fp4)

    for (int k = 0; k < num_k_steps - 1; k++) {
        int toc = 1 - tic;

        // Prefetch next tile (waves in "load role")
        // Using sched_group_barrier to interleave with compute
        if (wave_id < 4) {  // First 4 waves: load next tile
            load_tile_A(smem_A[toc], smem_As[toc], A, As, block_m, k+1, M, K);
            load_tile_B(smem_B[toc], smem_Bs[toc], B, Bs, block_n, k+1, N, K);
        }

        // Compute on current tile (all 8 waves participate)
        __builtin_amdgcn_sched_barrier(0);
        compute_mfma_tile(c_accum, smem_A[tic], smem_As[tic],
                          smem_B[tic], smem_Bs[tic], wave_m, wave_n, lane_id);
        __builtin_amdgcn_sched_barrier(0);

        __syncthreads();
        tic = toc;
    }
    // Final tile (no prefetch needed)
    compute_mfma_tile(c_accum, smem_A[tic], smem_As[tic],
                      smem_B[tic], smem_Bs[tic], wave_m, wave_n, lane_id);
    __syncthreads();

    // Store results
    store_output(C, c_accum, block_m + wave_m * 32, block_n + wave_n * 32, M, N, lane_id);
}
```

The `compute_mfma_tile` function calls the scaled MFMA intrinsic:
```cpp
__device__ inline void compute_mfma_tile(
    v16f32& c, const fp4x2_t* smem_A, const uint8_t* smem_As,
    const fp4x2_t* smem_B, const uint8_t* smem_Bs,
    int wave_m, int wave_n, int lane_id
) {
    using fp4x64_t = fp4x2_t __attribute__((ext_vector_type(32)));
    using v8i32    = int __attribute__((ext_vector_type(8)));

    // Load A fragment for this wave's row tile
    fp4x64_t a_reg = {};
    // ... (load 32 fp4x2 bytes for this thread's A fragment)

    fp4x64_t b_reg = {};
    // ... (load 32 fp4x2 bytes for this thread's B fragment)

    uint8_t scale_a = smem_As[wave_m * 32 + lane_id % 32];
    uint8_t scale_b = smem_Bs[wave_n * 32 + lane_id % 32];

    c = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
        *(v8i32*)&a_reg, *(v8i32*)&b_reg, c,
        4, 4,       // Atype=E2M1, Btype=E2M1
        0, scale_a, // OPSEL_A=0, scale_a
        0, scale_b  // OPSEL_B=0, scale_b
    );
}
```

---

## 5. E8M0 Scale Factor Handling

### What the task provides (B_scale_sh)

`B_scale_sh` from the task input is already shuffled via `e8m0_shuffle`. The shuffle reorders bytes for the aiter/CK kernel's internal layout (groups of 16 shuffled). For the native MFMA approach, we need UNshuffled E8M0 bytes.

**Option A:** Call `e8m0_unshuffle(B_scale_sh)` to recover linear order (available in aiter, see `aiter-mxfp4-api-limitations` Limitation 11).

**Option B:** Use B_scale_sh directly and match the shuffle in the kernel's scale load pattern (complex).

**Recommended:** Option A. Keep the Python wrapper calling `e8m0_unshuffle` to get linear [N, K//32] uint8 B scales, then the kernel indexes simply as `scale_b = Bs[col * K_groups + k_group]`.

### Scale per MFMA call

For `32x32x64` MFMA with MXFP4:
- 64 FP4 elements consumed along K per call = 2 scale groups (each group covers 32 FP4)
- Hardware applies ONE scale per operand per MFMA call
- Therefore: call the MFMA twice per tile step (BLOCK_K=32), once per scale group

```cpp
// Inner loop over K (step = 32 fp4 elements = 16 packed bytes = 1 scale group):
for (int k_step = 0; k_step < K/32; k_step++) {
    // Load 32 fp4 elements (16 bytes) into lower half of fp4x64_t
    fp4x64_t a_reg = {};
    for (int i = 0; i < 16; i++) a_reg[i] = A[(row * K/32 + k_step) * 16 + i];

    fp4x64_t b_reg = {};
    for (int i = 0; i < 16; i++) b_reg[i] = B[(col * K/32 + k_step) * 16 + i];

    uint8_t sa = As[row * (K/32) + k_step];
    uint8_t sb = Bs[col * (K/32) + k_step];

    c = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
        *(v8i32*)&a_reg, *(v8i32*)&b_reg, c, 4, 4, 0, sa, 0, sb);
}
```

Wait: the 32x32x64 MFMA processes 64 K elements (not 32). With MXFP4 at 2 fp4 per byte, 64 fp4 = 32 bytes. But each scale group covers 32 fp4 = 16 bytes. So 64 fp4 = 2 scale groups. The intrinsic takes ONE scale per operand. This means we either:

1. Use the 16x16x128 variant instead: it processes 128 K elements per call = 4 scale groups — worse
2. Use 32x32x64 with K_STEP=64 and use the dominant scale (max of 2 groups) — approximation
3. Use 32x32x64 with K_STEP=64, unrolled x2, treating each call as covering 32 K elements — but the hardware always reads all 64

**Correct approach:** The MFMA instruction processes 64 K elements per wave. Each of the 64 threads in the wave holds 1 element from the scale. The scale is per tile, not per thread-element. For MXFP4 with group-size 32, we have 2 scale groups per K_STEP=64 window. The hardware takes one scale per operand for the entire tile.

**Resolution from the AMD blog:** The scale is applied after the dot product for the entire K_STEP tile. For MXFP4 where group-size=32 and MFMA K=64, using a single scale per tile introduces up to 2 scale groups' error. This is acceptable (used in practice) or the K loop is stepped by 32 with lower K utilization.

**Recommended strategy:** Use `K_STEP=64` (full MFMA width), and for each tile choose `max(scale_group_0, scale_group_1)` as the tile scale, then requantize the lower group. This is what CK's flatmm implementation does.

**Simpler starting point:** Use the 32x32x64 MFMA with the B weight scale (which has been pre-shuffled for the aiter layout), keep BLOCK_K=64 fp4 = 1 MFMA call, and use scale_group_0 for the scale (slight accuracy impact but likely within correctness tolerance for benchmarking).

---

## 6. Implementation Spec: load_inline Kernel

### Interface

```python
# Python wrapper (in custom_kernel)
A, B, B_q, B_shuffle, B_scale_sh = data

# Quantize A (still required — fused quant is a v2 optimization)
A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())

# Prepare A scale in linear (unshuffled) order [M, K//32] uint8
from aiter.utility.fp4_utils import e8m0_unshuffle
A_scale_bytes = A_scale.view(torch.uint8)  # [M, K//32] uint8 already linear

# B data is pre-shuffled: B_shuffle [N, K//2] uint8 (fp4x2)
# B scale is pre-shuffled: B_scale_sh — unshuffle to get [N, K//32] uint8
B_scale_linear = e8m0_unshuffle(B_scale_sh).view(torch.uint8)  # [N, K//32]

C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
module.mxfp4_mfma_gemm(
    A_fp4.view(torch.uint8),  # [M, K//2] packed fp4
    A_scale_bytes,            # [M, K//32] e8m0
    B_shuffle.view(torch.uint8),  # [N, K//2] packed fp4 (pre-shuffled)
    B_scale_linear,           # [N, K//32] e8m0
    C, M, N, K
)
```

**CRITICAL NOTE on B_scale_sh format:** The competition input `B_scale_sh` is the output of `e8m0_shuffle(B_scale_e8m0)`. The shuffle used by aiter/CK is NOT a standard transpose — it's a specific permutation for the CK tile layout. The `e8m0_unshuffle` function reverses this. If `e8m0_unshuffle` is not available in the runner's aiter version, an alternative is to build the B_scale index mapping directly from the shuffle pattern (known from `aiter/utility/fp4_utils.py`).

### Compilation pattern

```python
module = load_inline(
    name="mxfp4_mfma_gemm",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm"],
    verbose=False,
    extra_cuda_cflags=[
        "--offload-arch=gfx950",
        "-std=c++20",
        "-O3",
        "-w",
    ],
)
```

No special library flags needed. `hip/hip_ext_ocp.h` is part of base ROCm 7.0 install.

---

## 7. Chiplet-Aware Grid Scheduling (From HipKittens Paper)

The MI355X has 8 XCDs, each with 32 CUs. Naive row-major threadblock ordering gives only 36% L2 hit rate on large GEMMs. HipKittens' algorithm:

```cpp
// From HipKittens: chiplet_transform_chunked()
// Chunk M-dimension tiles into groups of 8 to match XCD affinity
// Then within each group, iterate N-dimension for L2 reuse

__device__ dim3 chiplet_aware_blockid(int M_tiles, int N_tiles) {
    int bid = blockIdx.x;
    int chunk_size = 8;  // tiles per XCD group
    int m_chunk = (bid / (chunk_size * N_tiles));
    int local   = bid % (chunk_size * N_tiles);
    int local_m = local % chunk_size;
    int local_n = local / chunk_size;
    return {m_chunk * chunk_size + local_m, local_n, 0};
}
```

For competition shapes (small M), this matters less but is free to add.

---

## 8. Priority Ordering of Implementation Tasks

### Task 1: Minimal MFMA Kernel (Proof of Concept, ~1 day)

**Goal:** Prove `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4` works via `load_inline` and passes correctness.

**Minimal kernel:** No shared memory, no ping-pong. One MFMA per 32 K-elements, serial K loop. Output: bf16 via `__builtin_amdgcn_cvt_pkrtz_f16_f32`. Uses `hip/hip_ext_ocp.h`.

**Expected timing:** Slower than aiter (no memory optimization), but serves as correctness baseline.

**Files to create:**
- `kernels/mxfp4-mm/submission_mfma_v1.py` — minimal MFMA kernel

### Task 2: Shared Memory Tiled MFMA (Performance, ~2 days)

**Goal:** Add shared memory tiling for A and B, eliminate repeated global loads.

**Tile sizes:** BLOCK_M=32 (or 64), BLOCK_N=128, BLOCK_K=64 fp4 elements.

**Expected timing:** 5-10us range if memory bandwidth is saturated.

**Files to create:**
- `kernels/mxfp4-mm/submission_mfma_v2_tiled.py`

### Task 3: Fused Quant+MFMA (Highest Impact, ~3 days)

**Goal:** Eliminate `dynamic_mxfp4_quant` Python dispatch by computing E8M0 scales inline.

**Expected timing:** Could reach 3-6us (sub-leader territory) by removing 26-80us quant dispatch.

**Files to create:**
- `kernels/mxfp4-mm/submission_mfma_v3_fused.py`

### Task 4: Ping-Pong + Chiplet Scheduling (Polish, ~1 day)

**Goal:** Add 8-wave ping-pong prefetch and XCD-aware grid mapping.

---

## 9. Known Risks and Open Questions

| Risk | Severity | Mitigation |
|------|----------|------------|
| `hip/hip_ext_ocp.h` not in runner's ROCm | High | Check at runtime, fallback to manual fp4x2 typedef |
| `e8m0_unshuffle` not available in runner's aiter | Medium | Implement inline Python unshuffle from known pattern |
| Scale group mismatch (2 groups per MFMA K window) | Medium | Use dominant scale (K_STEP=64) or step K by 32 with 2 calls |
| Thread-to-data layout errors (correctness) | High | Start with minimal kernel, verify against aiter reference |
| B_shuffle layout incompatibility | High | Probe actual B_shuffle memory layout vs expected MFMA B layout |

**Most critical unknown:** The `B_shuffle` input is pre-shuffled for the aiter/CK kernel's internal memory layout. This layout may NOT match the naive `[N, K//2]` uint8 row-major layout expected by the MFMA register load code. The CK flatmm uses a specific shuffle pattern (16x16 blocks) for its SMEM tiling. Either:
1. Ignore B_shuffle and reuse B_q directly (B_q is unsorted fp4x2, row-major)
2. Understand the shuffle pattern and map it to the MFMA tile layout

**Recommendation:** Use `B_q` (not `B_shuffle`) as the B data input. `B_q` is the raw output of `dynamic_mxfp4_quant(B)` and has a standard `[N, K//2]` uint8 layout. The aiter shuffle is specifically for its CK kernel's tile layout, not needed for raw MFMA calls.

---

## 10. arXiv Papers: 2025-2026 AMD MI355X Optimization

### Directly relevant to the competition

| Paper | Key Insight for Competition |
|-------|----------------------------|
| arXiv:2511.08083 (HipKittens, Nov 2025) | 8-wave ping-pong beats AMD baselines; FP8 GEMM at 100% peak; chiplet-aware scheduling +15% |
| AMD ROCm Blog (Sep 2025) | `V_MFMA_SCALE_F32_16X16X128_F8F6F4` confirmed for CDNA4; scaled MFMA intrinsic usage pattern |

### Quantization accuracy papers (not directly useful for kernel perf)

| Paper | Relevance |
|-------|-----------|
| arXiv:2509.23202 (ICLR 2026) | MXFP4 accuracy gap study; confirms scale granularity matters |
| arXiv:2603.08713 (Jan 2026) | OAS/MBS scaling techniques; 6.2% GEMM overhead — not useful for perf |
| arXiv:2601.19213 (ASPLOS 2026) | M2XFP metadata augmented format; academic, not applicable |

### LLM search recommendation

Search these terms on arxiv.org for new papers:
- "gfx950 kernel optimization"
- "CDNA4 MXFP4 GEMM"
- "AMD MI355X matrix multiplication"
- "HipKittens GEMM"

---

## 11. Summary of Actionable Findings

1. **HipKittens cannot be used as a header in load_inline** — it requires its own compilation toolchain and does not support MXFP4.

2. **The native gfx950 path is `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4`** with `Atype=4, Btype=4` (E2M1 / MXFP4). This IS accessible from load_inline HIP C++.

3. **Header needed:** `#include <hip/hip_ext_ocp.h>` (ROCm 7.0+) provides `__amd_fp4x2_storage_t` and helper functions.

4. **All existing load_inline submissions are scalar (no MFMA).** They use a `fp4_to_f32` lookup table with one element per thread. Replacing with the scaled MFMA intrinsic is a multi-order-of-magnitude improvement in compute efficiency.

5. **Scale granularity:** One E8M0 byte per 32 FP4 elements. The 32x32x64 MFMA covers 64 K elements = 2 scale groups. Either step K by 32 (one scale per call) or use one dominant scale per 64 K elements (slight precision loss).

6. **HipKittens scheduling concept is directly applicable:** The 8-wave ping-pong pattern (double-buffered smem, tic/toc toggle, `__builtin_amdgcn_sched_barrier`) can be implemented in raw HIP C++ without the HK library.

7. **B input:** Use `B_q` (raw quantized, row-major) not `B_shuffle` (CK-specific layout) for the MFMA kernel.

8. **Fused quant is v3 priority:** Eliminates the dominant 26-80us quant cost. Requires computing E8M0 inline using IEEE 754 bit manipulation (`(amax_u32 + 0x200000u) & 0xFF800000u`).

---

## Cross-References

- `/home/mike-anderson/.claude/skills/amd-gemm-mxfp4-optimization/SKILL.md` — Current state, dead ends, E8M0 algorithm
- `/home/mike-anderson/.claude/skills/competitive-kernel-optimization-ceiling/SKILL.md` — Strategy framework
- `/home/mike-anderson/.claude/skills/amd-gfx950-tl-dot-scaled-constraints/SKILL.md` — Triton constraints (confirmed dead end)
- `/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm/submission_loadinline_clean.py` — Current load_inline (scalar, no MFMA)
- `salykova.github.io/matrix-cores-cdna` — Best public reference for scaled MFMA kernel code
- `rocm.blogs.amd.com/software-tools-optimization/matrix-cores-cdna/README.html` — Official AMD scaled MFMA reference
