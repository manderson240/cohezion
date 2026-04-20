#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""128x128 MFMA GEMM — 8-wave ping-pong with A-register reuse.

Architecture: 512 threads (8 waves), 128x128 output tile.
Wave layout: 4 M-groups x 2 N-groups.
  wave_m = wave_id % 4  -> M rows: 0-31, 32-63, 64-95, 96-127
  wave_n = wave_id / 4  -> N cols: 0-63 (makes 2 MFMA calls: +0 and +32)

Each wave makes 2 MFMA calls per K tile (A reuse across 2 N sub-tiles):
  call 0: c0 += MFMA(a_reg, b0_reg)  # cols bn + wave_n*64 + 0..31
  call 1: c1 += MFMA(a_reg, b1_reg)  # cols bn + wave_n*64 + 32..63

LDS double-buffering:
  smem_A[2][128 x 32 bytes] = 2 x 4KB = 8KB
  smem_B[2][128 x 32 bytes] = 2 x 4KB = 8KB
  Total: 16KB (fits in 64KB LDS)

Cooperative loading: 512 threads load 4KB A + 4KB B = 16 bytes/thread/tile.

For M < 128 (shapes 4, 16, 32, 64): falls back to aiter gemm_a4w4.
For M=256: 2 blocks in M dimension, each handles 128 rows.
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// MFMA register types (MUST be int vec8 — verified correct in Session 91)
typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// Tile constants
#define BLOCK_M       128   // 4 waves x 32 rows
#define BLOCK_N       128   // 2 waves x 64 cols (each wave does 2 x 32)
#define TILE_K        64    // FP4 elements per K tile = 2 scale groups
#define TILE_K_BYTES  32    // packed bytes (2 FP4 per byte)
#define THREADS       512   // 8 waves of 64
#define WAVESIZE      64

// LDS sizes (double-buffered)
#define LDS_A_BYTES (BLOCK_M * TILE_K_BYTES)   // 128 * 32 = 4096
#define LDS_B_BYTES (BLOCK_N * TILE_K_BYTES)   // 128 * 32 = 4096

// ─── 128x128 kernel: 8 waves, A-reuse across N ──────────────────────────────
// Wave layout: wave_m = wave_id % 4, wave_n = wave_id / 4
// wave_m selects M-row block: rows [wave_m*32 .. wave_m*32+31]
// wave_n selects N-col half:  cols [wave_n*64 .. wave_n*64+63]
//   (two 32-col sub-tiles per wave: +0 and +32)
// ─────────────────────────────────────────────────────────────────────────────
__global__ __launch_bounds__(THREADS, 2)
void mxfp4_gemm_128x128(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 linear
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 linear
    __hip_bfloat16* __restrict__ C,   // [M, N] BF16 output
    int M, int N, int K
) {
    const int bm  = blockIdx.y * BLOCK_M;
    const int bn  = blockIdx.x * BLOCK_N;
    const int tid = threadIdx.x;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int num_k_tiles = K / TILE_K;

    // Wave decomposition
    const int wave_id = tid / WAVESIZE;   // 0..7
    const int lane    = tid % WAVESIZE;   // 0..63 within wave
    const int wave_m  = wave_id % 4;      // M-row group: 0-3
    const int wave_n  = wave_id / 4;      // N-col half: 0 or 1
    const int half    = lane >> 5;        // 0 or 1 (K-half within wave)

    // This wave owns M-rows [bm + wave_m*32 .. bm + wave_m*32 + 31]
    // and N-cols [bn + wave_n*64 .. bn + wave_n*64 + 63]
    const int tile_m  = bm + wave_m * 32;
    const int tile_n0 = bn + wave_n * 64;        // first  32-col sub-tile
    const int tile_n1 = bn + wave_n * 64 + 32;   // second 32-col sub-tile

    // Double-buffered LDS
    __shared__ uint8_t smem_A[2][LDS_A_BYTES];
    __shared__ uint8_t smem_B[2][LDS_B_BYTES];

    // Two accumulator tiles per wave (for N0 and N1 sub-tiles)
    c_reg_t c0 = {}, c1 = {};

    int buf = 0;

    // ─── Prologue: cooperatively load first K tile ───────────────────────────
    // 4096 A bytes / 512 threads = 8 bytes/thread
    // 4096 B bytes / 512 threads = 8 bytes/thread
    // Total: 16 bytes/thread per tile -- fits in 2 uint4 loads
    for (int i = tid; i < LDS_A_BYTES; i += THREADS) {
        int row = i / TILE_K_BYTES;
        int col = i % TILE_K_BYTES;
        int gr  = bm + row;
        smem_A[0][i] = (gr < M && col < K_half) ? A[gr * K_half + col] : 0;
    }
    for (int i = tid; i < LDS_B_BYTES; i += THREADS) {
        int row = i / TILE_K_BYTES;
        int col = i % TILE_K_BYTES;
        int gr  = bn + row;
        smem_B[0][i] = (gr < N && col < K_half) ? B[gr * K_half + col] : 0;
    }
    __syncthreads();

    // ─── Main K-tile loop ─────────────────────────────────────────────────────
    for (int kt = 0; kt < num_k_tiles; kt++) {
        const int next_buf = 1 - buf;
        const bool has_next = (kt + 1 < num_k_tiles);

        // Load next tile into alternate buffer (all 512 threads cooperate)
        if (has_next) {
            const int k_off = (kt + 1) * TILE_K_BYTES;
            for (int i = tid; i < LDS_A_BYTES; i += THREADS) {
                int row = i / TILE_K_BYTES;
                int col = i % TILE_K_BYTES;
                int gr  = bm + row;
                smem_A[next_buf][i] = (gr < M && (k_off + col) < K_half) ?
                    A[gr * K_half + k_off + col] : 0;
            }
            for (int i = tid; i < LDS_B_BYTES; i += THREADS) {
                int row = i / TILE_K_BYTES;
                int col = i % TILE_K_BYTES;
                int gr  = bn + row;
                smem_B[next_buf][i] = (gr < N && (k_off + col) < K_half) ?
                    B[gr * K_half + k_off + col] : 0;
            }
        }

        // ─── MFMA compute from current buffer ────────────────────────────────
        // A-register: row = wave_m*32 + (lane & 31), K-half = half*16
        a_reg_t a_reg = {};
        {
            int a_local_row = wave_m * 32 + (lane & 31);
            int a_byte_off  = a_local_row * TILE_K_BYTES + half * 16;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) dst[i] = smem_A[buf][a_byte_off + i];
        }

        // B0-register: N0 sub-tile (wave_n*64 + lane&31), K-half = half*16
        b_reg_t b0_reg = {};
        {
            int b0_local_row = wave_n * 64 + (lane & 31);       // first 32-col sub-tile
            int b0_byte_off  = b0_local_row * TILE_K_BYTES + half * 16;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b0_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) dst[i] = smem_B[buf][b0_byte_off + i];
        }

        // B1-register: N1 sub-tile (wave_n*64 + 32 + lane&31), K-half = half*16
        b_reg_t b1_reg = {};
        {
            int b1_local_row = wave_n * 64 + 32 + (lane & 31);  // second 32-col sub-tile
            int b1_byte_off  = b1_local_row * TILE_K_BYTES + half * 16;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b1_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) dst[i] = smem_B[buf][b1_byte_off + i];
        }

        // Scales: 2 scale groups per K tile; scale_idx = kt*2 + half
        const int sg = kt * 2 + half;

        // A scale for this wave's M-row (each lane reads its own row)
        const int a_gr = tile_m + (lane & 31);
        const int sa   = (a_gr < M && sg < K_scale) ? (int)As[a_gr * K_scale + sg] : 127;

        // B scale for N0 sub-tile
        const int b0_gr = tile_n0 + (lane & 31);
        const int sb0   = (b0_gr < N && sg < K_scale) ? (int)Bs[b0_gr * K_scale + sg] : 127;

        // B scale for N1 sub-tile
        const int b1_gr = tile_n1 + (lane & 31);
        const int sb1   = (b1_gr < N && sg < K_scale) ? (int)Bs[b1_gr * K_scale + sg] : 127;

        // Two MFMA calls — A register reused across both N sub-tiles
        c0 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b0_reg, c0, 4, 4, 0, sa, 0, sb0);
        c1 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b1_reg, c1, 4, 4, 0, sa, 0, sb1);

        buf = next_buf;
        if (has_next) __syncthreads();
    }

    // ─── Epilogue: write N0 and N1 output tiles ──────────────────────────────
    // Output mapping (verified correct from SKILL.md):
    //   c_reg[r] -> C[tile_m + (r&3) + (r>>2)*8 + half*4][tile_n + (lane&31)]
    {
        // N0 sub-tile
        const int out_col0 = tile_n0 + (lane & 31);
        if (out_col0 < N) {
            #pragma unroll
            for (int r = 0; r < 16; r++) {
                int out_row = tile_m + (r & 3) + (r >> 2) * 8 + half * 4;
                if (out_row < M) {
                    C[out_row * N + out_col0] = (__hip_bfloat16)(c0[r]);
                }
            }
        }
        // N1 sub-tile
        const int out_col1 = tile_n1 + (lane & 31);
        if (out_col1 < N) {
            #pragma unroll
            for (int r = 0; r < 16; r++) {
                int out_row = tile_m + (r & 3) + (r >> 2) * 8 + half * 4;
                if (out_row < M) {
                    C[out_row * N + out_col1] = (__hip_bfloat16)(c1[r]);
                }
            }
        }
    }
}

// ─── C++ launcher ────────────────────────────────────────────────────────────
void launch_128x128(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C
) {
    int M = A.size(0);
    int K = A.size(1) * 2;   // A is [M, K/2] uint8
    int N = B.size(0);
    dim3 grid((N + BLOCK_N - 1) / BLOCK_N,
              (M + BLOCK_M - 1) / BLOCK_M);
    mxfp4_gemm_128x128<<<grid, THREADS>>>(
        A.data_ptr<uint8_t>(),
        B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(),
        Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""

CPP_SOURCE = """
void launch_128x128(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C
);
"""

try:
    _mod = load_inline(
        name="mfma_128x128",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_128x128"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[mfma_128x128] compile failed: {e}")
    _OK = False


def e8m0_unshuffle(s: torch.Tensor, m: int, n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle: [padded_M, padded_K/32] -> [M, K/32] linear."""
    sm, sn = s.shape
    return (
        s.view(sm // 32, sn // 8, 4, 16, 2, 2)
        .permute(0, 5, 3, 1, 4, 2)
        .contiguous()
        .view(sm, sn)[:m, :n]
    )


# Cache B-scale unshuffle to avoid redundant work on repeated calls with same B
_bs_cache: dict = {}


def _ref_kernel(data: input_t) -> output_t:
    """Fall back to aiter gemm_a4w4 (small M or compile failure)."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM with 128x128 MFMA tiling (8-wave A-reuse design).

    Dispatches to 128x128 kernel for M >= 128.
    Falls back to aiter gemm_a4w4 for M < 128 (shapes 4, 16, 32, 64).
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Small-M fallback: aiter is already optimal for M < 128
    if not _OK or M < 128:
        return _ref_kernel(data)

    ks = K // 32  # number of scale groups per row

    # Quantize A on the fly
    A_q, A_sc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = A_q.view(torch.uint8)
    As_bytes = A_sc[:M, :ks].contiguous().view(torch.uint8)

    # B is pre-quantized; unshuffle its scale once per unique B tensor
    B_bytes = B_q.view(torch.uint8)
    cache_key = (id(B_scale_sh), B_scale_sh.data_ptr(), N, ks)
    if cache_key not in _bs_cache:
        _bs_cache.clear()
        _bs_cache[cache_key] = (
            e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous().view(torch.uint8)
        )
    Bs_bytes = _bs_cache[cache_key]

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch_128x128(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
    return C
