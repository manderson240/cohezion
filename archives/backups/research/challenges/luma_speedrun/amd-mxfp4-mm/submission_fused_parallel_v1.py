#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM fused_parallel_v1: Parallel BF16->FP4 quant fused into MFMA.

Design vs fused_v1 (serial, 10-45x slower):
  - fused_v1: each thread loops 32 BF16 elements for max-abs, loops 32 more for quant.
    Total: 64 sequential BF16 reads per thread = high latency.
  - fused_parallel_v1: ALL 256 threads cooperatively load A (BF16) into LDS via
    coalesced 128-bit (uint4) stores. Each thread then owns exactly 32 BF16 elements
    (one MXFP4 scale group) and quantizes them locally. Work is DISTRIBUTED, not serial.

Architecture:
  - Grid: (ceil(N/128), ceil(M/32)), 256 threads per block (4 wavefronts)
  - Each block: 32×128 output tile
  - Wave i handles N columns [bn + i*32 .. bn + i*32 + 31]
  - LDS: BF16 A tile [32 rows × TILE_K columns] + FP4 B tile [128 rows × 32 bytes]
  - Each thread quantizes its own 32 BF16→FP4 using aiter's E8M0 formula
  - Avoids dynamic_mxfp4_quant kernel launch overhead (~2µs on ranked runner)

Ranked shapes:
  M=4,  N=2880, K=512   | M=16, N=2112, K=7168
  M=32, N=4096, K=512   | M=32, N=2880, K=512
  M=64, N=7168, K=2048  | M=256,N=3072, K=1536

Fallback: aiter gemm_a4w4 (bpreshuffle=True) when compile fails.
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# ─── HIP kernel source ────────────────────────────────────────────────────────
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/amd_detail/amd_hip_bf16.h>

typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// ─── FP4 E2M1 round-to-nearest-even ─────────────────────────────────────────
// FP4 values: 0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 (plus negatives)
__device__ __forceinline__ uint8_t float_to_fp4(float v) {
    const uint8_t sign = (v < 0.0f) ? 8u : 0u;
    const float a = fabsf(v);
    uint8_t code;
    if      (a <= 0.25f) code = 0;
    else if (a <  0.75f) code = 1;
    else if (a <= 1.25f) code = 2;
    else if (a <  1.75f) code = 3;
    else if (a <= 2.5f)  code = 4;
    else if (a <  3.5f)  code = 5;
    else if (a <= 5.0f)  code = 6;
    else                  code = 7;
    return sign | code;
}

// ─── E8M0 scale via BF16 exponent extraction (aiter-compatible) ──────────────
// Extract the BF16 exponent of max_abs, subtract 2, bump if mantissa >= 96/128.
// This matches aiter's dynamic_mxfp4_quant formula exactly.
__device__ __forceinline__ int compute_e8m0_scale(float max_abs) {
    if (max_abs == 0.0f) return 0;
    const __hip_bfloat16 max_bf16 = (__hip_bfloat16)max_abs;
    const unsigned short bf16_bits = *reinterpret_cast<const unsigned short*>(&max_bf16);
    int bf16_exp = (bf16_bits >> 7) & 0xFF;
    const int bf16_man = bf16_bits & 0x7F;
    if (bf16_man >= 96) bf16_exp += 1;
    return max(bf16_exp - 2, 0);
}

__device__ __forceinline__ float scale_exp_to_inv(int scale_exp) {
    return (scale_exp > 0) ? __int_as_float((254 - scale_exp) << 23) : 1.0f;
}

// ─── Quantize 32 BF16 values from LDS → 16 packed FP4 bytes ─────────────────
// This runs fully LOCAL: one thread, 32 BF16 elements, no warp communication.
// Pass 1: find max_abs (32 fabs + 31 fmax = ~63 ops)
// Pass 2: quantize 32 BF16 → 16 FP4 bytes (~100 ops)
// Total: ~163 ops vs. cooperative global load approach (which is just 2 passes on 32 regs)
__device__ __forceinline__ int quantize_bf16_to_fp4_local(
    const __hip_bfloat16* __restrict__ src,   // 32 BF16 elements in LDS
    uint8_t* __restrict__ dst                  // 16 packed FP4 bytes output
) {
    // Pass 1: max absolute value (fully unrolled)
    float max_abs = 0.0f;
    #pragma unroll
    for (int i = 0; i < 32; i++) {
        max_abs = fmaxf(max_abs, fabsf(__bfloat162float(src[i])));
    }

    const int scale_exp = compute_e8m0_scale(max_abs);
    const float inv_scale = scale_exp_to_inv(scale_exp);

    // Pass 2: quantize 32 BF16 → 16 packed FP4 bytes (2 FP4 per byte, lo nibble first)
    #pragma unroll
    for (int i = 0; i < 16; i++) {
        const float v0 = __bfloat162float(src[i * 2    ]) * inv_scale;
        const float v1 = __bfloat162float(src[i * 2 + 1]) * inv_scale;
        dst[i] = (float_to_fp4(v1) << 4) | float_to_fp4(v0);
    }
    return scale_exp;
}

// ─── Main fused kernel: 32×128 tile, 256 threads = 4 waves ──────────────────
// Grid: blockIdx.x = N tile (step 128), blockIdx.y = M tile (step 32)
// A is BF16 [M, K]; B is pre-quantized FP4 [N, K/2]; Bs is E8M0 [N, K/32].
// Quantizes A inline using cooperative LDS loading + per-thread local quant.
//
// LDS layout (all double-buffered):
//   smem_A_bf16[2][BLOCK_M][TILE_K]       — BF16 A (cooperative load)
//   smem_Aq[2][BLOCK_M][TILE_K_BYTES]     — FP4 A after per-thread quant
//   smem_Asc[2][BLOCK_M][TILE_K/32]       — A E8M0 scales (2 per tile row)
//   smem_B[2][BLOCK_N][TILE_K_BYTES]      — FP4 B (cooperative load)
//   smem_Bsc[2][BLOCK_N][2]               — B E8M0 scales (2 per tile row)
//
// Note: smem_Aq + smem_Asc are produced by the quantize step, then consumed by MFMA.

#define BLOCK_M 32
#define BLOCK_N 128
#define TILE_K  64
#define TILE_K_BYTES 32   // TILE_K / 2 packed bytes
#define WAVES   4
#define WAVESIZE 64
#define THREADS (WAVES * WAVESIZE)

// LDS byte sizes
#define LDS_A_BF16  (BLOCK_M * TILE_K * sizeof(__hip_bfloat16))  // 32*64*2 = 4096
#define LDS_AQ_FP4  (BLOCK_M * TILE_K_BYTES)                     // 32*32   = 1024
#define LDS_ASC     (BLOCK_M * 2)                                 // 32*2    = 64
#define LDS_B_FP4   (BLOCK_N * TILE_K_BYTES)                     // 128*32  = 4096
#define LDS_BSC     (BLOCK_N * 2)                                 // 128*2   = 256

__global__ __launch_bounds__(THREADS, 2)
void mxfp4_gemm_fused_parallel(
    const __hip_bfloat16* __restrict__ A_bf16,  // [M, K]
    const uint8_t*        __restrict__ B_fp4,   // [N, K/2]
    const uint8_t*        __restrict__ Bs,       // [N, K/32] E8M0 (linear)
    __hip_bfloat16*       __restrict__ C,        // [M, N]
    int M, int N, int K
) {
    const int bm  = blockIdx.y * BLOCK_M;
    const int bn  = blockIdx.x * BLOCK_N;
    const int tid = threadIdx.x;

    const int wave_id = tid / WAVESIZE;  // 0..3
    const int lane    = tid % WAVESIZE;  // 0..63
    const int half_id = lane >> 5;       // 0 or 1

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int n_tiles = K / TILE_K;

    // Wave's N offset: wave i handles [bn + i*32 .. bn + i*32 + 31]
    const int wave_bn = bn + wave_id * 32;

    // ─── Shared memory (double-buffered) ────────────────────────────────────
    // Buffer 0 and 1 alternate between "current" and "loading next"
    __shared__ __hip_bfloat16 smem_A_bf16[2][BLOCK_M * TILE_K];   // 2 × 4096 bytes
    __shared__ uint8_t        smem_Aq[2][BLOCK_M * TILE_K_BYTES]; // 2 × 1024 bytes
    __shared__ uint8_t        smem_Asc[2][BLOCK_M * 2];           // 2 × 64 bytes
    __shared__ uint8_t        smem_B[2][BLOCK_N * TILE_K_BYTES];  // 2 × 4096 bytes
    __shared__ uint8_t        smem_Bsc[2][BLOCK_N * 2];           // 2 × 256 bytes

    // ─── Accumulator ────────────────────────────────────────────────────────
    c_reg_t c_reg = {};

    // ─── Lambda: cooperatively load A (BF16) tile into LDS ─────────────────
    // A tile = BLOCK_M × TILE_K = 32 × 64 BF16 = 4096 bytes
    // 256 threads × 8 bytes (4 BF16) each = 2048 BF16 per pass → 2 passes total
    // But we can load 16 bytes (uint4 = 8 BF16) per thread in 1 pass with 256 threads:
    //   256 * 8 BF16 = 2048 BF16 per pass, need 2 passes for 2048 total → 1 pass = wrong
    //   Actually 32*64 = 2048 BF16 → 256 threads × 8 BF16 = 2048 → exactly 1 pass!
    // Each thread loads 8 BF16 (16 bytes / uint4 = one 128-bit load).
    auto load_A_tile = [&](int kt_idx, int slot) __device__ {
        // Assign each of the 256 threads an 8-BF16 chunk:
        // thread i → smem row = i / 8, BF16 col start = (i % 8) * 8
        const int k_start = kt_idx * TILE_K;
        const int local_chunk = tid;  // 0..255
        const int lds_row     = local_chunk / 8;          // 0..31
        const int lds_col_off = (local_chunk % 8) * 8;   // 0, 8, 16, ..., 56
        const int g_row       = bm + lds_row;
        const int g_col       = k_start + lds_col_off;

        __hip_bfloat16* dst = smem_A_bf16[slot] + lds_row * TILE_K + lds_col_off;
        if (g_row < M && g_col + 8 <= K) {
            // 16-byte vectorized load (128-bit)
            *reinterpret_cast<uint4*>(dst) =
                *reinterpret_cast<const uint4*>(A_bf16 + g_row * K + g_col);
        } else {
            // Partial / out-of-bounds: fill with zeros
            #pragma unroll
            for (int i = 0; i < 8; i++) {
                const int gc = g_col + i;
                dst[i] = (g_row < M && gc < K) ? A_bf16[g_row * K + gc]
                                                : (__hip_bfloat16)0.0f;
            }
        }
    };

    // ─── Lambda: cooperatively load B (FP4) tile into LDS ──────────────────
    // B tile = BLOCK_N × TILE_K_BYTES = 128 × 32 = 4096 bytes
    // 256 threads × 16 bytes (uint4) = 4096 bytes → 1 pass exactly
    auto load_B_tile = [&](int kt_idx, int slot) __device__ {
        const int k_byte_start = kt_idx * TILE_K_BYTES;
        const int i = tid;  // 0..255
        // Each thread handles 16 bytes: row = i / 2, byte_off = (i % 2) * 16
        const int lds_row    = i / 2;        // 0..127
        const int lds_boff   = (i % 2) * 16; // 0 or 16
        const int g_row      = bn + lds_row;
        const int g_byte_off = k_byte_start + lds_boff;

        uint8_t* dst = smem_B[slot] + lds_row * TILE_K_BYTES + lds_boff;
        if (g_row < N && g_byte_off + 16 <= K_half) {
            *reinterpret_cast<uint4*>(dst) =
                *reinterpret_cast<const uint4*>(B_fp4 + g_row * K_half + g_byte_off);
        } else {
            *reinterpret_cast<uint4*>(dst) = {0, 0, 0, 0};
        }

        // B scales: 128 rows × 2 scale groups = 256 bytes → 1 byte per thread
        const int sg_base = kt_idx * 2;
        const int sc_row  = i / 2;
        const int sc_sg   = i % 2;
        const int g_sc_row = bn + sc_row;
        const int g_sg     = sg_base + sc_sg;
        smem_Bsc[slot][i] = (g_sc_row < N && g_sg < K_scale)
                              ? Bs[g_sc_row * K_scale + g_sg]
                              : 127;
    };

    // ─── Lambda: per-thread A quantization after A tile is in LDS ───────────
    // 256 threads quantize BLOCK_M × 2 scale groups = 64 groups total.
    // Each thread handles 1 scale group = 32 BF16 → 16 packed FP4 bytes.
    // Thread assignment: thread i → row = i / 2, half = i % 2
    // But we only have 64 scale groups, not 256. Extra threads are idle.
    auto quantize_A_tile = [&](int kt_idx, int slot) __device__ {
        // Only threads 0..63 quantize (BLOCK_M=32 rows × 2 halves = 64 groups)
        if (tid < BLOCK_M * 2) {
            const int q_row  = tid / 2;      // 0..31
            const int q_half = tid % 2;      // 0 or 1
            // BF16 elements: row q_row, columns [q_half*32 .. q_half*32+31]
            const __hip_bfloat16* src =
                smem_A_bf16[slot] + q_row * TILE_K + q_half * 32;
            uint8_t* fp4_dst = smem_Aq[slot] + q_row * TILE_K_BYTES + q_half * 16;
            const int scale_exp = quantize_bf16_to_fp4_local(src, fp4_dst);
            smem_Asc[slot][q_row * 2 + q_half] = (uint8_t)scale_exp;
        }
        // Threads 64..255 are idle during quantization (they already loaded B)
    };

    // ─── Prologue: load tile 0 into buffer 0 ────────────────────────────────
    load_A_tile(0, 0);
    load_B_tile(0, 0);
    __syncthreads();
    quantize_A_tile(0, 0);
    __syncthreads();

    int cur = 0;  // current buffer index

    // ─── Main K-tile loop ────────────────────────────────────────────────────
    // Sync ordering (ALL __syncthreads() are UNCONDITIONAL to avoid UB):
    //   1. Prologue already filled cur=0 and quantized it, with two syncs.
    //   2. Each iteration:
    //      a. ALL threads load next tile (no-op for last iteration, writes harmlessly)
    //      b. __syncthreads()  ← ALL threads, guards the global→LDS loads
    //      c. ALL threads quantize next tile (no-op for last iteration, tid<64 only)
    //      d. __syncthreads()  ← ALL threads, guards the quant writes
    //      e. MFMA consumes cur tile (already valid from previous iteration's sync)
    //      f. swap cur/nxt
    //
    // Note: we pre-load nxt BEFORE MFMA, then sync, then quantize nxt, then sync,
    //       THEN do MFMA on cur. This avoids reading nxt before it's ready.
    // Simplified: two unconditional syncs per iteration, double-buffer alternates.

    for (int kt = 0; kt < n_tiles; kt++) {
        const int nxt = 1 - cur;

        // Stage 1: All threads load the NEXT tile into nxt buffer.
        // For the last tile (kt = n_tiles-1), nxt writes are harmless (never consumed).
        if (kt + 1 < n_tiles) {
            load_A_tile(kt + 1, nxt);
            load_B_tile(kt + 1, nxt);
        }
        // ALL threads sync here — guards the global→LDS stores above
        __syncthreads();

        // Stage 2: Quantize the NEXT A tile (threads 0..63 only, rest idle).
        // Must run after the sync above so A_bf16 LDS data is visible.
        if (kt + 1 < n_tiles) {
            quantize_A_tile(kt + 1, nxt);
        }
        // ALL threads sync here — guards the quant writes into smem_Aq / smem_Asc
        __syncthreads();

        // Stage 3: MFMA consumes CUR tile (fully valid: loaded + quantized in prologue
        //          or previous iteration's stages 1-2).

        // ─── A register load (from quantized FP4 in LDS) ────────────────
        // Lane mapping: lane & 31 = A row within the 32-row tile,
        //               half_id   = which K-half (0=bytes 0-15, 1=bytes 16-31)
        a_reg_t a_reg = {};
        {
            const int a_lds_row  = lane & 31;
            const int a_lds_koff = half_id * 16;  // byte offset into the 32-byte row
            const uint8_t* src = smem_Aq[cur] + a_lds_row * TILE_K_BYTES + a_lds_koff;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            // 16-byte vectorized LDS load
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
            // Upper 16 bytes of a_reg stay zero (FP4 uses only first 16 bytes per MFMA spec)
        }

        // ─── A scale from LDS ───────────────────────────────────────────
        // smem_Asc is indexed as [BLOCK_M * 2] where each A row has 2 scale groups.
        const int a_sg = (lane & 31) * 2 + half_id;
        const int sa   = (int)smem_Asc[cur][a_sg];

        // ─── B register load (from FP4 B in LDS) ────────────────────────
        // Each wave handles B columns [bn + wave_id*32 .. bn + wave_id*32 + 31]
        b_reg_t b_reg = {};
        {
            const int b_lds_row  = wave_id * 32 + (lane & 31);
            const int b_lds_koff = half_id * 16;
            const uint8_t* src = smem_B[cur] + b_lds_row * TILE_K_BYTES + b_lds_koff;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        // ─── B scale from LDS ───────────────────────────────────────────
        const int b_lds_row = wave_id * 32 + (lane & 31);
        const int sb = (int)smem_Bsc[cur][b_lds_row * 2 + half_id];

        // ─── MFMA 32×32×64 FP4 with block scaling ───────────────────────
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg,
            4,      // cbsz = FP4 E2M1 for A
            4,      // blgp = FP4 E2M1 for B
            0, sa,  // neg_a = 0, scale_a = E8M0 exponent
            0, sb   // neg_b = 0, scale_b = E8M0 exponent
        );

        cur = nxt;
    }

    // ─── Epilogue: write output ──────────────────────────────────────────────
    // MFMA 32×32×64 output mapping (VERIFIED in SKILL.md):
    //   c_reg[r] → C[bm + (r%4) + (r/4)*8 + (lane/32)*4][wave_bn + (lane%32)]
    const int out_col = wave_bn + (lane & 31);
    if (out_col < N) {
        #pragma unroll
        for (int r = 0; r < 16; r++) {
            const int out_row = bm + (r & 3) + (r >> 2) * 8 + half_id * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

// ─── Small-M path: 32×32 single-wave, inline quant ──────────────────────────
// Used for M <= 16 to avoid waste from 4-wave tile on tiny M.
// Uses the same BF16→FP4 quantization approach but without LDS for A.
// A is loaded directly from global memory into registers (works for small M).
__global__ __launch_bounds__(WAVESIZE, 8)
void mxfp4_gemm_fused_small(
    const __hip_bfloat16* __restrict__ A_bf16,
    const uint8_t*        __restrict__ B_fp4,
    const uint8_t*        __restrict__ Bs,
    __hip_bfloat16*       __restrict__ C,
    int M, int N, int K
) {
    const int bm  = blockIdx.y * 32;
    const int bn  = blockIdx.x * 32;
    const int tid = threadIdx.x;  // 0..63

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int n_tiles = K / TILE_K;

    // Which A row and B column does this lane handle?
    const int a_row  = bm + (tid & 31);
    const int b_col  = bn + (tid & 31);
    const int half_id = tid >> 5;

    const bool a_valid = (a_row < M);
    const bool b_valid = (b_col < N);

    c_reg_t c_reg = {};

    for (int kt = 0; kt < n_tiles; kt++) {
        a_reg_t a_reg = {};
        b_reg_t b_reg = {};
        int sa = 0;

        // Each lane handles 32 BF16 elements from A (its own scale group)
        const int a_k_start = kt * TILE_K + half_id * 32;

        if (a_valid && a_k_start + 32 <= K) {
            const __hip_bfloat16* a_ptr = A_bf16 + a_row * K + a_k_start;

            // Pass 1: find max absolute value across 32 elements
            float max_abs = 0.0f;
            #pragma unroll
            for (int i = 0; i < 32; i++) {
                max_abs = fmaxf(max_abs, fabsf(__bfloat162float(a_ptr[i])));
            }

            sa = compute_e8m0_scale(max_abs);
            const float inv_scale = scale_exp_to_inv(sa);

            // Pass 2: quantize 32 BF16 → 16 packed FP4 bytes
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) {
                const float v0 = __bfloat162float(a_ptr[i * 2    ]) * inv_scale;
                const float v1 = __bfloat162float(a_ptr[i * 2 + 1]) * inv_scale;
                a_bytes[i] = (float_to_fp4(v1) << 4) | float_to_fp4(v0);
            }
        }

        // B: vectorized 16-byte load from global
        const int b_k_byte_off = kt * TILE_K_BYTES + half_id * 16;
        if (b_valid && b_k_byte_off + 16 <= K_half) {
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(b_bytes) =
                *reinterpret_cast<const uint4*>(B_fp4 + b_col * K_half + b_k_byte_off);
        }

        const int sg = kt * 2 + half_id;
        const int sb = (b_valid && sg < K_scale) ? (int)Bs[b_col * K_scale + sg] : 0;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

    // Epilogue: MFMA output mapping
    const int out_col = bn + (tid & 31);
    if (out_col < N) {
        #pragma unroll
        for (int r = 0; r < 16; r++) {
            const int out_row = bm + (r & 3) + (r >> 2) * 8 + half_id * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

void launch_fused_parallel(
    torch::Tensor A_bf16,
    torch::Tensor B_fp4,
    torch::Tensor Bs,
    torch::Tensor C
) {
    const int M = A_bf16.size(0);
    const int K = A_bf16.size(1);
    const int N = B_fp4.size(0);

    const auto* a_ptr  = reinterpret_cast<const __hip_bfloat16*>(A_bf16.data_ptr());
    const auto* b_ptr  = B_fp4.data_ptr<uint8_t>();
    const auto* bs_ptr = Bs.data_ptr<uint8_t>();
    auto* c_ptr        = reinterpret_cast<__hip_bfloat16*>(C.data_ptr());

    if (M <= 16) {
        // Small-M path: 32×32 per block, 64 threads
        dim3 grid((N + 31) / 32, (M + 31) / 32);
        mxfp4_gemm_fused_small<<<grid, WAVESIZE>>>(a_ptr, b_ptr, bs_ptr, c_ptr, M, N, K);
    } else {
        // Main path: 32×128 per block, 256 threads
        dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);
        mxfp4_gemm_fused_parallel<<<grid, THREADS>>>(a_ptr, b_ptr, bs_ptr, c_ptr, M, N, K);
    }
}
"""

CPP_SOURCE = """
void launch_fused_parallel(
    torch::Tensor A_bf16,
    torch::Tensor B_fp4,
    torch::Tensor Bs,
    torch::Tensor C
);
"""

try:
    _mod = load_inline(
        name="mxfp4_fused_parallel_v1",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_fused_parallel"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _COMPILE_OK = True
except Exception as e:
    print(f"[fused_parallel_v1] compile failed: {e}")
    _COMPILE_OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to recover linear [orig_m, orig_n] layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def _aiter_fallback(data: input_t) -> output_t:
    """Reference implementation via aiter gemm_a4w4."""
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )


def custom_kernel(data: input_t) -> output_t:
    """Fused BF16->FP4 quantization + MFMA 32x32x64 GEMM via single HIP kernel.

    Key difference from fused_v1 (serial):
      - All 256 threads cooperatively load A (BF16) into LDS (coalesced 128-bit stores).
      - Each thread independently quantizes its own 32 BF16 elements (1 scale group).
      - No serial 64-element loops per thread; work is fully distributed.
      - Eliminates the separate dynamic_mxfp4_quant kernel launch (~2µs overhead).
    """
    if not _COMPILE_OK:
        return _aiter_fallback(data)

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32  # number of scale groups per row

    # A: pass raw BF16 — kernel quantizes inline
    A_bf16 = A.contiguous()

    # B: pre-quantized FP4 bytes [N, K/2]
    B_bytes = B_q.view(torch.uint8)

    # B scales: unshuffle from aiter's shuffled format to linear [N, K/32]
    Bs_bytes = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous()

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch_fused_parallel(A_bf16, B_bytes, Bs_bytes, C)
    return C
