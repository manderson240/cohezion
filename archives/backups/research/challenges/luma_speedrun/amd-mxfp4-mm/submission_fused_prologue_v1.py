#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM fused_prologue_v1: PROLOGUE-ONLY quantization.

Problem with fused_parallel_v1:
  - Quantizes A at EVERY K-tile iteration.
  - For K=7168 with TILE_K=64: 112 re-quantizations of the same A data!

Fix — PROLOGUE quantization:
  1. PROLOGUE (once per K-chunk): all threads cooperatively load A BF16 into LDS,
     then quantize the entire chunk to FP4 + E8M0 scales in LDS.
  2. INNER K-TILE LOOP: reads pre-quantized A from LDS (NO quantization),
     loads B from global, runs MFMA 32x32x64.
  3. Outer loop advances to next K-chunk with a fresh prologue.

Architecture:
  - Grid: (ceil(N/128), ceil(M/32)), 256 threads (4 wavefronts)
  - Each block: 32 M-rows × 128 N-columns output tile
  - CHUNK_K = 512 FP4 elements per row (8 MFMA tiles per chunk)
  - LDS layout:
      union {
        smem_A_bf16[32][512]  — BF16 staging (32KB, overlapped with FP4 store area)
      };
      smem_Aq[32][256]       — FP4 A after prologue quant (8KB)
      smem_Asc[32][16]       — E8M0 scales after prologue quant (512 bytes)
      Total LDS: ~40KB (fits in 64KB)
  - B loaded directly from global each tile (avoids extra 4KB/tile LDS pressure)

LDS savings vs fused_parallel_v1:
  - fused_parallel_v1 quantizes A per tile (TILE_K=64) → calls quant 2×per tile × N_tiles
  - fused_prologue_v1 quantizes A per chunk (CHUNK_K=512) → calls quant 16×per chunk
    (32 rows × CHUNK_K/32=16 scale groups = 512 quant units per chunk vs same!)
  - But the quant is called ONCE per chunk, not once per MFMA tile → 8x fewer quant rounds
  - For K=7168: 14 chunks × 1 prologue vs 112 tiles × 1 quant = 8x reduction

Benchmark target: beat fused_parallel_v1 (123-1544µs) and approach mfma_v1 (19-52µs).

Ranked shapes:
  M=4,  N=2880, K=512   | M=16, N=2112, K=7168
  M=32, N=4096, K=512   | M=32, N=2880, K=512
  M=64, N=7168, K=2048  | M=256,N=3072, K=1536

Fallback: aiter gemm_a4w4 when compile fails.
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


# ─── HIP kernel source ────────────────────────────────────────────────────────
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/amd_detail/amd_hip_bf16.h>

// MFMA register types (MUST be int vec8, NOT uint8_t vectors!)
typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// ─── FP4 E2M1 round-to-nearest-even ─────────────────────────────────────────
// Representable magnitudes: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0
// Ties round toward even mantissa (LSB=0).
__device__ __forceinline__ uint8_t float_to_fp4(float v) {
    const uint8_t sign = (v < 0.0f) ? 8u : 0u;
    const float a = fabsf(v);
    uint8_t code;
    if      (a <= 0.25f) code = 0;  // even: mantissa 0
    else if (a <  0.75f) code = 1;
    else if (a <= 1.25f) code = 2;  // even: mantissa 0
    else if (a <  1.75f) code = 3;
    else if (a <= 2.5f)  code = 4;  // even: mantissa 0
    else if (a <  3.5f)  code = 5;
    else if (a <= 5.0f)  code = 6;  // even: mantissa 0
    else                  code = 7;
    return sign | code;
}

// ─── E8M0 scale via BF16 exponent extraction (aiter-compatible) ──────────────
// Matches aiter's dynamic_mxfp4_quant formula exactly (reverse-engineered Session 91).
__device__ __forceinline__ int compute_e8m0_scale(float max_abs) {
    if (max_abs == 0.0f) return 0;
    const __hip_bfloat16 max_bf16 = (__hip_bfloat16)max_abs;
    const unsigned short bf16_bits = *reinterpret_cast<const unsigned short*>(&max_bf16);
    int bf16_exp = (bf16_bits >> 7) & 0xFF;
    const int bf16_man = bf16_bits & 0x7F;
    if (bf16_man >= 96) bf16_exp += 1;
    return max(bf16_exp - 2, 0);
}

// Compute float inverse of 2^scale_exp.
__device__ __forceinline__ float scale_exp_to_inv(int scale_exp) {
    return (scale_exp > 0) ? __int_as_float((254 - scale_exp) << 23) : 1.0f;
}

// ─── Quantize 32 BF16 values → 16 packed FP4 bytes (1 scale group) ───────────
// Returns E8M0 scale exponent (also writes 16 bytes to dst).
__device__ __forceinline__ int quantize_group_32(
    const __hip_bfloat16* __restrict__ src,  // 32 BF16 elements (in LDS or regs)
    uint8_t* __restrict__ dst                // 16 packed FP4 bytes output
) {
    float max_abs = 0.0f;
    #pragma unroll
    for (int i = 0; i < 32; i++) {
        max_abs = fmaxf(max_abs, fabsf(__bfloat162float(src[i])));
    }
    const int scale_exp = compute_e8m0_scale(max_abs);
    const float inv = scale_exp_to_inv(scale_exp);
    #pragma unroll
    for (int i = 0; i < 16; i++) {
        const float v0 = __bfloat162float(src[i * 2    ]) * inv;
        const float v1 = __bfloat162float(src[i * 2 + 1]) * inv;
        dst[i] = (float_to_fp4(v1) << 4) | float_to_fp4(v0);
    }
    return scale_exp;
}

// ─── Constants ───────────────────────────────────────────────────────────────
#define BLOCK_M    32    // M rows per block
#define BLOCK_N   128    // N cols per block (4 waves × 32)
#define TILE_K     64    // FP4 elements per MFMA K-dimension
#define TILE_K_B   32    // bytes per tile (TILE_K/2, packed)
#define WAVES       4
#define WAVESIZE   64
#define THREADS   256    // WAVES * WAVESIZE

// PROLOGUE chunk size: how many FP4 K-elements to quantize at once.
// 512 FP4 per row → 8 MFMA tiles per chunk.
// LDS for BF16 staging: 32*512*2 = 32KB
// LDS for FP4 result:   32*256   =  8KB
// LDS for E8M0 scales:  32*16    = 512B
// Total: ~40.5KB (fits in 64KB CU budget)
#define CHUNK_K      512   // FP4 elements per chunk per row
#define CHUNK_K_B    256   // bytes per chunk per row (CHUNK_K/2)
#define CHUNK_TILES  8     // CHUNK_K / TILE_K
#define CHUNK_SCALES 16    // CHUNK_K / 32 (scale groups per row per chunk)

// ─── LDS union: BF16 staging overlaps with FP4 output ────────────────────────
// Phase 1 (prologue): fill smem_A_bf16 (32KB), then quantize into smem_Aq (8KB).
// Phase 2 (MFMA):     read from smem_Aq (BF16 buffer not needed anymore this chunk).
// We do NOT union them in HIP C++ (aliasing rules), but since prologue completes
// before MFMA begins (protected by __syncthreads), we can safely use separate arrays
// and rely on the compiler/hardware to pack them efficiently given LDS bank structure.
//
// Total LDS: 32KB + 8KB + 512B = ~40.5KB per block. Fine for MI355X (64KB/CU).

// ─── Main kernel: 32×128 tile, 256 threads (4 waves) ─────────────────────────
// Each block computes C[bm:bm+32, bn:bn+128].
// A: BF16 [M, K], B: pre-quantized FP4 [N, K/2], Bs: E8M0 [N, K/32] linear.
__global__ __launch_bounds__(THREADS, 1)
void mxfp4_gemm_prologue(
    const __hip_bfloat16* __restrict__ A_bf16,
    const uint8_t*        __restrict__ B_fp4,
    const uint8_t*        __restrict__ Bs,
    __hip_bfloat16*       __restrict__ C,
    int M, int N, int K
) {
    const int bm  = blockIdx.y * BLOCK_M;
    const int bn  = blockIdx.x * BLOCK_N;
    const int tid = threadIdx.x;

    const int wave_id = tid / WAVESIZE;  // 0..3
    const int lane    = tid % WAVESIZE;  // 0..63
    const int half_id = lane >> 5;       // 0 or 1 (which 16-byte half of MFMA tile)

    const int K_half  = K / 2;
    const int K_scale = K / 32;

    // This wave's N-column range
    const int wave_bn = bn + wave_id * 32;

    // ─── LDS buffers ──────────────────────────────────────────────────────────
    // BF16 staging for A (32 rows × CHUNK_K BF16 = 32KB)
    __shared__ __hip_bfloat16 smem_A_bf16[BLOCK_M * CHUNK_K];
    // FP4 A after prologue quantization (32 rows × CHUNK_K_B bytes = 8KB)
    __shared__ uint8_t smem_Aq[BLOCK_M * CHUNK_K_B];
    // E8M0 scales for A (32 rows × CHUNK_SCALES = 512 bytes)
    __shared__ uint8_t smem_Asc[BLOCK_M * CHUNK_SCALES];

    // Accumulator (fp32, zeroed)
    c_reg_t c_reg = {};

    // Number of full K-chunks
    const int n_chunks = K / CHUNK_K;
    const int rem_k    = K % CHUNK_K;  // 0 when K is divisible by CHUNK_K

    // Outer loop: one prologue per K-chunk
    for (int ck = 0; ck < n_chunks + (rem_k > 0 ? 1 : 0); ck++) {
        const int k_chunk_start = ck * CHUNK_K;
        const int this_chunk_k  = (ck < n_chunks) ? CHUNK_K : rem_k;
        const int this_chunk_kb = this_chunk_k / 2;

        // ── PROLOGUE: cooperatively load A BF16 chunk → LDS ─────────────────
        // A BF16 tile: BLOCK_M rows × CHUNK_K columns = 32 × 512 = 16384 BF16 elements.
        // 256 threads × 8 BF16/thread (uint4 = 16 bytes) = 2048 per pass.
        // Need 16384 / 2048 = 8 passes. Each thread handles 8 evenly-spaced chunks.
        // Stride: THREADS = 256 chunks of 8 BF16 = 2048 BF16 per stride step.
        // Total chunks: BLOCK_M * CHUNK_K / 8 = 32 * 64 = 2048 → 8 per thread.
        {
            const int total_chunks = BLOCK_M * (CHUNK_K / 8);  // 2048
            for (int i = tid; i < total_chunks; i += THREADS) {
                const int lds_row     = i / (CHUNK_K / 8);        // 0..31
                const int lds_col_off = (i % (CHUNK_K / 8)) * 8;  // 0, 8, .., 504
                const int g_row       = bm + lds_row;
                const int g_col       = k_chunk_start + lds_col_off;

                __hip_bfloat16* dst = smem_A_bf16 + lds_row * CHUNK_K + lds_col_off;
                if (g_row < M && g_col + 8 <= K) {
                    *reinterpret_cast<uint4*>(dst) =
                        *reinterpret_cast<const uint4*>(A_bf16 + g_row * K + g_col);
                } else if (g_row < M) {
                    #pragma unroll
                    for (int j = 0; j < 8; j++) {
                        const int gc = g_col + j;
                        dst[j] = (gc < K) ? A_bf16[g_row * K + gc] : (__hip_bfloat16)0.0f;
                    }
                } else {
                    *reinterpret_cast<uint4*>(dst) = {0, 0, 0, 0};
                }
            }
        }
        __syncthreads();  // ALL threads: guard BF16 LDS writes

        // ── PROLOGUE: cooperatively quantize A BF16 chunk → FP4 + E8M0 ──────
        // CHUNK_SCALES = 16 scale groups per row, BLOCK_M = 32 rows → 512 groups total.
        // 256 threads → each handles 2 scale groups. Threads 0..255 all participate.
        {
            // Thread i → handles 2 scale groups:
            //   group 0: row = i / CHUNK_SCALES, sg = i % CHUNK_SCALES
            //   group 1: row = (i + THREADS) / CHUNK_SCALES, sg = (i + THREADS) % CHUNK_SCALES
            // Actually: BLOCK_M * CHUNK_SCALES = 32 * 16 = 512 groups total.
            // THREADS = 256 → each thread handles exactly 2 groups.
            const int total_groups = BLOCK_M * CHUNK_SCALES;  // 512
            const int groups_per_thread = total_groups / THREADS;  // 2

            #pragma unroll
            for (int g = 0; g < groups_per_thread; g++) {
                const int grp_id = tid * groups_per_thread + g;  // 0..511
                const int q_row  = grp_id / CHUNK_SCALES;        // 0..31
                const int q_sg   = grp_id % CHUNK_SCALES;        // 0..15

                const __hip_bfloat16* src =
                    smem_A_bf16 + q_row * CHUNK_K + q_sg * 32;
                uint8_t* fp4_dst = smem_Aq + q_row * CHUNK_K_B + q_sg * 16;

                // Skip groups beyond this chunk's actual K range
                const int k_elem_start = q_sg * 32;
                if (k_elem_start < this_chunk_k) {
                    const int scale_exp = quantize_group_32(src, fp4_dst);
                    smem_Asc[q_row * CHUNK_SCALES + q_sg] = (uint8_t)scale_exp;
                } else {
                    // Zero-pad FP4 and neutral scale for partial trailing group
                    smem_Asc[q_row * CHUNK_SCALES + q_sg] = 0;
                    #pragma unroll
                    for (int b = 0; b < 16; b++) fp4_dst[b] = 0;
                }
            }
        }
        __syncthreads();  // ALL threads: guard FP4 + scale LDS writes

        // ── INNER K-TILE LOOP: MFMA consuming pre-quantized A from LDS ───────
        // No quantization here — A is already FP4 in smem_Aq.
        const int tiles_this_chunk = (this_chunk_k + TILE_K - 1) / TILE_K;

        for (int kt = 0; kt < tiles_this_chunk; kt++) {
            // ─ Load pre-quantized A from LDS (NO quantization!) ──────────────
            // MFMA A mapping: lane & 31 = row in [0,31]; half_id = which 16-byte half.
            a_reg_t a_reg = {};
            {
                const int a_lds_row  = lane & 31;
                const int a_lds_koff = (kt * TILE_K_B) + half_id * 16;
                const uint8_t* src = smem_Aq + a_lds_row * CHUNK_K_B + a_lds_koff;
                uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
                *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
                // Upper 16 bytes of a_reg stay zero (FP4 MFMA uses only first 16 bytes)
            }

            // ─ A scale from LDS ───────────────────────────────────────────────
            // smem_Asc indexed as [row * CHUNK_SCALES + sg_in_chunk].
            // Row = lane & 31, scale group within chunk = kt * 2 + half_id.
            // CHUNK_SCALES=16 >= tiles_this_chunk*2 always (max CHUNK_TILES*2 = 16).
            const int a_sg = (lane & 31) * CHUNK_SCALES + (kt * 2 + half_id);
            const int sa   = (int)smem_Asc[a_sg];

            // ─ Load B from global memory (pre-quantized FP4 [N, K/2]) ─────────
            // B column for this lane: wave_bn + (lane & 31)
            b_reg_t b_reg = {};
            {
                const int b_col      = wave_bn + (lane & 31);
                const int b_k_byte   = (k_chunk_start / 2) + kt * TILE_K_B + half_id * 16;
                if (b_col < N && b_k_byte + 16 <= K_half) {
                    uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
                    *reinterpret_cast<uint4*>(dst) =
                        *reinterpret_cast<const uint4*>(B_fp4 + b_col * K_half + b_k_byte);
                }
            }

            // ─ B scale from global ────────────────────────────────────────────
            const int b_col    = wave_bn + (lane & 31);
            const int b_sg_idx = (k_chunk_start / 32) + kt * 2 + half_id;
            const int sb = (b_col < N && b_sg_idx < K_scale)
                           ? (int)Bs[b_col * K_scale + b_sg_idx]
                           : 0;

            // ─ MFMA 32×32×64 FP4 with E8M0 block scaling ─────────────────────
            c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                a_reg, b_reg, c_reg,
                4,      // cbsz = FP4 E2M1 for A
                4,      // blgp = FP4 E2M1 for B
                0, sa,  // neg_a=0, scale_a
                0, sb   // neg_b=0, scale_b
            );
        }
        // No __syncthreads needed here: LDS reads in inner loop are all done
        // before this chunk's outer iteration ends. Next prologue has its own sync.
    }

    // ─── Epilogue: write output ──────────────────────────────────────────────
    // MFMA 32×32×64 output mapping (VERIFIED in SKILL.md Session 91):
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

// ─── Small-M kernel: 32×32 tile, 64 threads (1 wave) ─────────────────────────
// For M <= 16: single wavefront handles 32×32 output tile with global-memory-only
// A quantization (no LDS needed — A is small enough to load into registers).
#define SMALL_BLOCK_M 32
#define SMALL_BLOCK_N 32

__global__ __launch_bounds__(WAVESIZE, 8)
void mxfp4_gemm_prologue_small(
    const __hip_bfloat16* __restrict__ A_bf16,
    const uint8_t*        __restrict__ B_fp4,
    const uint8_t*        __restrict__ Bs,
    __hip_bfloat16*       __restrict__ C,
    int M, int N, int K
) {
    const int bm  = blockIdx.y * SMALL_BLOCK_M;
    const int bn  = blockIdx.x * SMALL_BLOCK_N;
    const int tid = threadIdx.x;  // 0..63

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int n_tiles = K / TILE_K;

    const int a_row   = bm + (tid & 31);
    const int b_col   = bn + (tid & 31);
    const int half_id = tid >> 5;

    const bool a_valid = (a_row < M);
    const bool b_valid = (b_col < N);

    c_reg_t c_reg = {};

    for (int kt = 0; kt < n_tiles; kt++) {
        a_reg_t a_reg = {};
        int sa = 0;

        // Each lane quantizes its own 32 BF16 → 16 FP4 bytes (1 scale group)
        const int a_k_start = kt * TILE_K + half_id * 32;
        if (a_valid && a_k_start + 32 <= K) {
            const __hip_bfloat16* a_ptr = A_bf16 + a_row * K + a_k_start;

            float max_abs = 0.0f;
            #pragma unroll
            for (int i = 0; i < 32; i++) {
                max_abs = fmaxf(max_abs, fabsf(__bfloat162float(a_ptr[i])));
            }
            sa = compute_e8m0_scale(max_abs);
            const float inv = scale_exp_to_inv(sa);

            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) {
                const float v0 = __bfloat162float(a_ptr[i * 2    ]) * inv;
                const float v1 = __bfloat162float(a_ptr[i * 2 + 1]) * inv;
                a_bytes[i] = (float_to_fp4(v1) << 4) | float_to_fp4(v0);
            }
        }

        b_reg_t b_reg = {};
        const int b_k_byte = kt * TILE_K_B + half_id * 16;
        if (b_valid && b_k_byte + 16 <= K_half) {
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(b_bytes) =
                *reinterpret_cast<const uint4*>(B_fp4 + b_col * K_half + b_k_byte);
        }

        const int sg = kt * 2 + half_id;
        const int sb = (b_valid && sg < K_scale) ? (int)Bs[b_col * K_scale + sg] : 0;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

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

// ─── Host-side launcher ──────────────────────────────────────────────────────
void launch_prologue(
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
        // Small-M: single-wave 32×32 tiles
        dim3 grid((N + 31) / 32, (M + 31) / 32);
        mxfp4_gemm_prologue_small<<<grid, WAVESIZE>>>(
            a_ptr, b_ptr, bs_ptr, c_ptr, M, N, K);
    } else {
        // Main: 4-wave 32×128 tiles
        dim3 grid((N + 127) / 128, (M + 31) / 32);
        mxfp4_gemm_prologue<<<grid, THREADS>>>(
            a_ptr, b_ptr, bs_ptr, c_ptr, M, N, K);
    }
}
"""

CPP_SOURCE = """
void launch_prologue(
    torch::Tensor A_bf16,
    torch::Tensor B_fp4,
    torch::Tensor Bs,
    torch::Tensor C
);
"""

try:
    _mod = load_inline(
        name="mxfp4_fused_prologue_v1",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_prologue"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _COMPILE_OK = True
except Exception as e:
    print(f"[fused_prologue_v1] compile failed: {e}")
    _COMPILE_OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle: [sm, sn] shuffled → [orig_m, orig_n] linear."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def _aiter_fallback(data: input_t) -> output_t:
    """Reference implementation via aiter gemm_a4w4 (used when HIP compile fails)."""
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
    """Fused BF16→FP4 quant + MFMA GEMM with PROLOGUE-ONLY quantization.

    Key improvement over fused_parallel_v1:
      - A is quantized ONCE per K-chunk (CHUNK_K=512 FP4 elements) in a prologue.
      - The inner MFMA loop reads pre-quantized A from LDS (zero quant overhead).
      - For K=7168: 14 prologue rounds vs 112 per-tile quant rounds = 8x reduction.
      - For K=512:  1 prologue round (identical to parallel but with better LDS use).
    """
    if not _COMPILE_OK:
        return _aiter_fallback(data)

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Validate K is divisible by TILE_K=64 (required for MFMA loop)
    assert K % 64 == 0, f"K={K} must be divisible by 64 for MFMA tiles"

    # A: raw BF16, kernel quantizes inline during prologue
    A_bf16 = A.contiguous()

    # B: pre-quantized FP4 bytes [N, K/2]
    B_bytes = B_q.view(torch.uint8)

    # B scales: unshuffle from aiter's shuffled format to linear [N, K/32]
    ks = K // 32
    Bs_bytes = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous()

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch_prologue(A_bf16, B_bytes, Bs_bytes, C)
    return C
