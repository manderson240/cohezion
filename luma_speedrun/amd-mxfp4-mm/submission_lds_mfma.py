#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: LDS-tiled FP4 MFMA with cooperative loading.

Combines:
- ROCm CDNA4 blog's cooperative LDS loading pattern (all threads help load tiles)
- Our verified FP4 MFMA 32×32 compute (correct register layout)
- Double-buffered K-tile loop
- 4 waves per block (256 threads) → 4 MFMA tiles per K iteration

Architecture:
- Block tile: 64×128 (M×N) — 2×4 grid of 32×32 MFMA tiles
- 256 threads = 4 waves of 64
- Each wave handles one 32×32 MFMA tile in the M dimension
- LDS: double-buffered A[64×K_BYTES] + B[128×K_BYTES] = 2×(2KB+4KB) = 12KB
- Cooperative loading: 256 threads load A+B tiles in parallel
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// Tile sizes
#define BLOCK_M 64     // M tiles: 2 × 32
#define BLOCK_N 128    // N tiles: 4 × 32
#define TILE_K 64      // FP4 elements per K tile
#define TILE_K_BYTES 32
#define THREADS 256    // 4 waves
#define WAVESIZE 64

// LDS layout: double-buffered
// A: [2][BLOCK_M][TILE_K_BYTES] = 2 × 64 × 32 = 4096 bytes
// B: [2][BLOCK_N][TILE_K_BYTES] = 2 × 128 × 32 = 8192 bytes
// Total: 12288 bytes — fits easily in 160KB LDS
#define LDS_A_SIZE (BLOCK_M * TILE_K_BYTES)    // 2048
#define LDS_B_SIZE (BLOCK_N * TILE_K_BYTES)    // 4096

__global__ __launch_bounds__(THREADS, 4)
void mxfp4_gemm_lds(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    // Block position
    int bm = blockIdx.y * BLOCK_M;
    int bn = blockIdx.x * BLOCK_N;
    int tid = threadIdx.x;

    int K_half = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / TILE_K;

    // Wave ID and lane within wave
    int wave_id = tid / WAVESIZE;   // 0-3
    int lane_id = tid % WAVESIZE;   // 0-63

    // Each wave handles a 32×32 MFMA tile
    // Wave layout: 2 waves in M × 2 waves in N
    // wave 0: M[0:32] × N[0:32]
    // wave 1: M[0:32] × N[32:64]
    // wave 2: M[32:64] × N[0:32]
    // wave 3: M[32:64] × N[32:64]
    int wave_m = wave_id / 2;  // 0 or 1
    int wave_n = wave_id % 2;  // 0 or 1

    // But we want 4 N tiles, not 2. Use 2 passes over N.
    // Alternative: wave layout = 1×4 (all waves share M, spread across N)
    // wave 0: N[0:32], wave 1: N[32:64], wave 2: N[64:96], wave 3: N[96:128]
    // This is better for small M (decode shapes where M=4-16)
    wave_m = 0;  // All waves share the same M rows
    wave_n = wave_id;  // Each wave handles different N columns

    // MFMA register position within wave
    int half_id = lane_id >> 5;  // 0 or 1 within wave
    int mfma_row = bm + wave_m * 32 + (lane_id & 31);
    int mfma_col_base = bn + wave_n * 32;

    // Double-buffered LDS
    __shared__ uint8_t smem_A[2][LDS_A_SIZE];
    __shared__ uint8_t smem_B[2][LDS_B_SIZE];

    // Accumulators — each wave accumulates over K for its 32×32 tile
    // For BLOCK_M=64 with wave_m=0, we process M in 2 passes
    c_reg_t c_reg0 = {};  // M rows [0:32]
    c_reg_t c_reg1 = {};  // M rows [32:64]
    for (int i = 0; i < 16; i++) { c_reg0[i] = 0.0f; c_reg1[i] = 0.0f; }

    int buf = 0;

    // ─── Prologue: Cooperative load first K tile ──────────────────────
    {
        // A tile: 64 × 32 = 2048 bytes / 256 threads = 8 bytes/thread
        for (int i = tid; i < LDS_A_SIZE; i += THREADS) {
            int row = i / TILE_K_BYTES;
            int col = i % TILE_K_BYTES;
            int gr = bm + row;
            smem_A[0][i] = (gr < M && col < K_half) ? A[gr * K_half + col] : 0;
        }
        // B tile: 128 × 32 = 4096 bytes / 256 threads = 16 bytes/thread
        for (int i = tid; i < LDS_B_SIZE; i += THREADS) {
            int row = i / TILE_K_BYTES;
            int col = i % TILE_K_BYTES;
            int gr = bn + row;
            smem_B[0][i] = (gr < N && col < K_half) ? B[gr * K_half + col] : 0;
        }
    }
    __syncthreads();

    // ─── Main K-tile loop ────────────────────────────────────────────
    for (int kt = 0; kt < num_k_tiles; kt++) {
        int next_kt = kt + 1;
        int next_buf = 1 - buf;

        // ─── Async load next tile (double-buffer) ────────────────────
        if (next_kt < num_k_tiles) {
            int k_off = next_kt * TILE_K_BYTES;
            for (int i = tid; i < LDS_A_SIZE; i += THREADS) {
                int row = i / TILE_K_BYTES;
                int col = i % TILE_K_BYTES;
                int gr = bm + row;
                smem_A[next_buf][i] = (gr < M && (k_off + col) < K_half) ?
                    A[gr * K_half + k_off + col] : 0;
            }
            for (int i = tid; i < LDS_B_SIZE; i += THREADS) {
                int row = i / TILE_K_BYTES;
                int col = i % TILE_K_BYTES;
                int gr = bn + row;
                smem_B[next_buf][i] = (gr < N && (k_off + col) < K_half) ?
                    B[gr * K_half + k_off + col] : 0;
            }
        }

        // ─── MFMA compute from LDS (current buffer) ─────────────────
        // Pass 1: M rows [0:32]
        {
            a_reg_t a_reg = {};
            b_reg_t b_reg = {};

            // Load A from LDS: lane reads from row (lane_id & 31), offset (half_id * 16)
            int a_row_local = lane_id & 31;  // 0-31
            int a_off = half_id * 16;
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            for (int i = 0; i < 16; i++) {
                a_bytes[i] = smem_A[buf][a_row_local * TILE_K_BYTES + a_off + i];
            }

            // Load B from LDS: lane reads from row (wave_n * 32 + lane_id & 31)
            int b_row_local = wave_n * 32 + (lane_id & 31);
            int b_off = half_id * 16;
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            for (int i = 0; i < 16; i++) {
                b_bytes[i] = smem_B[buf][b_row_local * TILE_K_BYTES + b_off + i];
            }

            // Scales (from global memory — small, likely cached)
            int sg = kt * 2 + half_id;
            int a_gr = bm + a_row_local;
            int b_gr = bn + wave_n * 32 + (lane_id & 31);
            int sa = (a_gr < M && sg < K_scale) ? (int)As[a_gr * K_scale + sg] : 127;
            int sb = (b_gr < N && sg < K_scale) ? (int)Bs[b_gr * K_scale + sg] : 127;

            c_reg0 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                a_reg, b_reg, c_reg0, 4, 4, 0, sa, 0, sb);
        }

        // Pass 2: M rows [32:64]
        if (bm + 32 < M) {
            a_reg_t a_reg = {};
            b_reg_t b_reg = {};

            int a_row_local = 32 + (lane_id & 31);
            int a_off = half_id * 16;
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            for (int i = 0; i < 16; i++) {
                a_bytes[i] = smem_A[buf][a_row_local * TILE_K_BYTES + a_off + i];
            }

            int b_row_local = wave_n * 32 + (lane_id & 31);
            int b_off = half_id * 16;
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            for (int i = 0; i < 16; i++) {
                b_bytes[i] = smem_B[buf][b_row_local * TILE_K_BYTES + b_off + i];
            }

            int sg = kt * 2 + half_id;
            int a_gr = bm + 32 + (lane_id & 31);
            int b_gr = bn + wave_n * 32 + (lane_id & 31);
            int sa = (a_gr < M && sg < K_scale) ? (int)As[a_gr * K_scale + sg] : 127;
            int sb = (b_gr < N && sg < K_scale) ? (int)Bs[b_gr * K_scale + sg] : 127;

            c_reg1 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                a_reg, b_reg, c_reg1, 4, 4, 0, sa, 0, sb);
        }

        buf = next_buf;
        if (next_kt < num_k_tiles) __syncthreads();
    }

    // ─── Write output ────────────────────────────────────────────────
    int out_col_base = mfma_col_base + (lane_id & 31);
    if (out_col_base < N) {
        // Pass 1 output: M rows [0:32]
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + half_id * 4;
            if (out_row < M) {
                C[out_row * N + out_col_base] = (__hip_bfloat16)(c_reg0[r]);
            }
        }
        // Pass 2 output: M rows [32:64]
        if (bm + 32 < M) {
            for (int r = 0; r < 16; r++) {
                int out_row = bm + 32 + (r & 3) + (r >> 2) * 8 + half_id * 4;
                if (out_row < M) {
                    C[out_row * N + out_col_base] = (__hip_bfloat16)(c_reg1[r]);
                }
            }
        }
    }
}

void launch(torch::Tensor A, torch::Tensor B,
            torch::Tensor As, torch::Tensor Bs, torch::Tensor C) {
    int M = A.size(0), K = A.size(1) * 2, N = B.size(0);
    dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);
    mxfp4_gemm_lds<<<grid, THREADS>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()), M, N, K);
}
"""

CPP_SOURCE = (
    "void launch(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor);"
)

try:
    _mod = load_inline(
        name="fp4mfma_lds",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[fp4mfma_lds] {e}")
    _OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    if not _OK:
        import aiter

        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)

    B_bytes = B_q.view(torch.uint8)
    Bs_unshuffled = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks)
    Bs_bytes = Bs_unshuffled.contiguous().view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
    return C
