#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: LDS-tiled FP4 MFMA v2 — optimized for small M, large N.

Competition shapes: M=4-256, N=2112-4096, K=512-7168.
Small M means N parallelism is critical.

Architecture:
- Block tile: 32×128 (M×N) — 1 M-tile × 4 N-tiles
- 256 threads = 4 waves, each wave handles one 32×32 MFMA
- LDS: double-buffered A[32×32] + B[128×32] = 2×(1KB+4KB) = 10KB
- Cooperative loading with 4-byte (int) aligned loads
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

#define BLOCK_M 32
#define BLOCK_N 128
#define TILE_K 64
#define TILE_K_BYTES 32
#define THREADS 256
#define WAVESIZE 64

#define LDS_A_SIZE (BLOCK_M * TILE_K_BYTES)   // 1024 bytes
#define LDS_B_SIZE (BLOCK_N * TILE_K_BYTES)   // 4096 bytes

__global__ __launch_bounds__(THREADS, 4)
void mxfp4_gemm_lds_v2(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    int bm = blockIdx.y * BLOCK_M;
    int bn = blockIdx.x * BLOCK_N;
    int tid = threadIdx.x;

    int K_half = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / TILE_K;

    int wave_id = tid / WAVESIZE;
    int lane_id = tid % WAVESIZE;
    int half_id = lane_id >> 5;

    // Wave layout: 1×4 (one M-tile, four N-tiles)
    int wave_n = wave_id;  // 0-3

    __shared__ uint8_t smem_A[2][LDS_A_SIZE];
    __shared__ uint8_t smem_B[2][LDS_B_SIZE];

    c_reg_t c_reg = {};
    for (int i = 0; i < 16; i++) c_reg[i] = 0.0f;

    int buf = 0;

    // ─── Prologue: Load first tile cooperatively ─────────────────────
    // A: 1024 bytes / 256 threads = 4 bytes/thread (1 int)
    // B: 4096 bytes / 256 threads = 16 bytes/thread (4 ints)
    {
        // A cooperative load (4 bytes per thread)
        for (int i = tid; i < LDS_A_SIZE / 4; i += THREADS) {
            int byte_idx = i * 4;
            int row = byte_idx / TILE_K_BYTES;
            int col = byte_idx % TILE_K_BYTES;
            int gr = bm + row;
            if (gr < M && col + 4 <= K_half) {
                *reinterpret_cast<int*>(&smem_A[0][byte_idx]) =
                    *reinterpret_cast<const int*>(&A[gr * K_half + col]);
            } else {
                // Byte-by-byte for boundary
                for (int j = 0; j < 4; j++) {
                    int c = col + j;
                    smem_A[0][byte_idx + j] = (gr < M && c < K_half) ?
                        A[gr * K_half + c] : 0;
                }
            }
        }
        // B cooperative load (16 bytes per thread — 4 iterations of 4 bytes)
        for (int i = tid; i < LDS_B_SIZE / 4; i += THREADS) {
            int byte_idx = i * 4;
            int row = byte_idx / TILE_K_BYTES;
            int col = byte_idx % TILE_K_BYTES;
            int gr = bn + row;
            if (gr < N && col + 4 <= K_half) {
                *reinterpret_cast<int*>(&smem_B[0][byte_idx]) =
                    *reinterpret_cast<const int*>(&B[gr * K_half + col]);
            } else {
                for (int j = 0; j < 4; j++) {
                    int c = col + j;
                    smem_B[0][byte_idx + j] = (gr < N && c < K_half) ?
                        B[gr * K_half + c] : 0;
                }
            }
        }
    }
    __syncthreads();

    // ─── Main K-tile loop with double-buffering ──────────────────────
    for (int kt = 0; kt < num_k_tiles; kt++) {
        int next_kt = kt + 1;
        int next_buf = 1 - buf;

        // Async load next tile
        if (next_kt < num_k_tiles) {
            int k_off = next_kt * TILE_K_BYTES;
            for (int i = tid; i < LDS_A_SIZE / 4; i += THREADS) {
                int byte_idx = i * 4;
                int row = byte_idx / TILE_K_BYTES;
                int col = byte_idx % TILE_K_BYTES;
                int gr = bm + row;
                if (gr < M && (k_off + col + 4) <= K_half) {
                    *reinterpret_cast<int*>(&smem_A[next_buf][byte_idx]) =
                        *reinterpret_cast<const int*>(&A[gr * K_half + k_off + col]);
                } else {
                    for (int j = 0; j < 4; j++) {
                        int c = k_off + col + j;
                        smem_A[next_buf][byte_idx + j] = (gr < M && c < K_half) ?
                            A[gr * K_half + c] : 0;
                    }
                }
            }
            for (int i = tid; i < LDS_B_SIZE / 4; i += THREADS) {
                int byte_idx = i * 4;
                int row = byte_idx / TILE_K_BYTES;
                int col = byte_idx % TILE_K_BYTES;
                int gr = bn + row;
                if (gr < N && (k_off + col + 4) <= K_half) {
                    *reinterpret_cast<int*>(&smem_B[next_buf][byte_idx]) =
                        *reinterpret_cast<const int*>(&B[gr * K_half + k_off + col]);
                } else {
                    for (int j = 0; j < 4; j++) {
                        int c = k_off + col + j;
                        smem_B[next_buf][byte_idx + j] = (gr < N && c < K_half) ?
                            B[gr * K_half + c] : 0;
                    }
                }
            }
        }

        // ─── MFMA compute from LDS ──────────────────────────────────
        a_reg_t a_reg = {};
        b_reg_t b_reg = {};

        // A from LDS: row = lane_id & 31, offset = half_id * 16
        int a_row_local = lane_id & 31;
        int a_off = half_id * 16;
        uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
        for (int i = 0; i < 16; i++) {
            a_bytes[i] = smem_A[buf][a_row_local * TILE_K_BYTES + a_off + i];
        }

        // B from LDS: row = wave_n * 32 + (lane_id & 31)
        int b_row_local = wave_n * 32 + (lane_id & 31);
        int b_off = half_id * 16;
        uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
        for (int i = 0; i < 16; i++) {
            b_bytes[i] = smem_B[buf][b_row_local * TILE_K_BYTES + b_off + i];
        }

        // Scales from global (small, likely L1/L2 cached)
        int sg = kt * 2 + half_id;
        int a_gr = bm + a_row_local;
        int b_gr = bn + wave_n * 32 + (lane_id & 31);
        int sa = (a_gr < M && sg < K_scale) ? (int)As[a_gr * K_scale + sg] : 127;
        int sb = (b_gr < N && sg < K_scale) ? (int)Bs[b_gr * K_scale + sg] : 127;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);

        buf = next_buf;
        if (next_kt < num_k_tiles) __syncthreads();
    }

    // ─── Write output ────────────────────────────────────────────────
    int out_col = bn + wave_n * 32 + (lane_id & 31);
    if (out_col < N) {
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + half_id * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

void launch(torch::Tensor A, torch::Tensor B,
            torch::Tensor As, torch::Tensor Bs, torch::Tensor C) {
    int M = A.size(0), K = A.size(1) * 2, N = B.size(0);
    dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);
    mxfp4_gemm_lds_v2<<<grid, THREADS>>>(
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
        name="fp4mfma_lds_v2",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[fp4mfma_lds_v2] {e}")
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
