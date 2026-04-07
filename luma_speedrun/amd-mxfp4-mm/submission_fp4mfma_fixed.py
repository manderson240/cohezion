#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: Native FP4 MFMA with CORRECTED output mapping.

Key fix: 32×32 output mapping is column-major per thread:
  c_reg[i*4+j] → C[(tid/32)*4 + j + i*8][tid % 32]
NOT row-major as previously assumed.

This matches the 16×16 BF16 MFMA pattern (c_reg[j] → C[(tid/16)*4+j][tid%16])
scaled up for 32×32 (2 halves of wavefront, 4 groups of 4 rows each).
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

using fp4x2_t = uint8_t;
typedef fp4x2_t fp4x64_t __attribute__((ext_vector_type(32)));
typedef float fp32x16_t __attribute__((ext_vector_type(16)));

#define TILE_M 32
#define TILE_N 32
#define TILE_K 64
#define TILE_K_BYTES 32
#define WAVESIZE 64

__global__ void mxfp4_gemm_fp4mfma(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    int bm = blockIdx.y * TILE_M;
    int bn = blockIdx.x * TILE_N;
    int tid = threadIdx.x;

    int K_half = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / TILE_K;

    // LDS for A and B tiles (contiguous 32×32 byte layout)
    __shared__ uint8_t lds_a[32 * 32];
    __shared__ uint8_t lds_b[32 * 32];

    fp32x16_t c_reg = {};
    for (int i = 0; i < 16; i++) c_reg[i] = 0.0f;

    for (int kt = 0; kt < num_k_tiles; kt++) {
        // Cooperative load into LDS (32×32 = 1024 bytes, 16 bytes/thread)
        for (int i = tid; i < 32 * 32; i += WAVESIZE) {
            int row = i / 32, col = i % 32;
            int gr = bm + row;
            int gc = kt * TILE_K_BYTES + col;
            lds_a[i] = (gr < M && gc < K_half) ? A[gr * K_half + gc] : 0;
        }
        for (int i = tid; i < 32 * 32; i += WAVESIZE) {
            int row = i / 32, col = i % 32;
            int gr = bn + row;
            int gc = kt * TILE_K_BYTES + col;
            lds_b[i] = (gr < N && gc < K_half) ? B[gr * K_half + gc] : 0;
        }
        __syncthreads();

        // Read from LDS using blog pattern
        fp4x64_t a_reg = {};
        fp4x64_t b_reg = {};

        // A: thread t reads row (t%32), K-half (t/32)
        const uint8_t* ldg_a = lds_a + (tid % 32) * 32 + (tid / 32) * 16;
        for (int i = 0; i < 16; i++) a_reg[i] = ldg_a[i];

        // B: blog pattern with interleaving
        const uint8_t* ldg_b = lds_b + (tid % 32) / 2 + 16 * 32 * (tid / 32);
        int b_ext = tid % 2;
        for (int i = 0; i < 16; i++) {
            uint8_t by0 = *(ldg_b + 16 * 2 * i);
            uint8_t by1 = *(ldg_b + 16 * (2 * i + 1));
            uint8_t v0 = b_ext ? ((by0 >> 4) & 0xF) : (by0 & 0xF);
            uint8_t v1 = b_ext ? ((by1 >> 4) & 0xF) : (by1 & 0xF);
            b_reg[i] = v0 | (v1 << 4);
        }

        // Scales (A: per thread, B: representative)
        int sg = kt * 2 + (tid / 32);
        int a_row = bm + (tid % 32);
        uint8_t sa = (a_row < M && sg < K_scale) ? As[a_row * K_scale + sg] : 127;
        int b_rep = bn + 16 * (tid / 32);
        uint8_t sb = (b_rep < N && sg < K_scale) ? Bs[b_rep * K_scale + sg] : 127;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);

        __syncthreads();
    }

    // CORRECTED 32×32 output mapping (column-major per thread):
    // c_reg[i*4+j] → C[(tid/32)*4 + j + i*8][tid % 32]
    // Thread column = tid % 32
    // Thread writes to 4 groups of 4 consecutive rows:
    //   tid/32=0: rows {0-3, 8-11, 16-19, 24-27}
    //   tid/32=1: rows {4-7, 12-15, 20-23, 28-31}
    int out_col = bn + (tid % 32);
    if (out_col < N) {
        for (int i = 0; i < 4; i++) {
            int row_base = bm + (tid / 32) * 4 + i * 8;
            for (int j = 0; j < 4; j++) {
                int out_row = row_base + j;
                if (out_row < M) {
                    C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[i * 4 + j]);
                }
            }
        }
    }
}

void launch(torch::Tensor A, torch::Tensor B,
            torch::Tensor As, torch::Tensor Bs, torch::Tensor C) {
    int M = A.size(0), K = A.size(1) * 2, N = B.size(0);
    dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
    mxfp4_gemm_fp4mfma<<<grid, WAVESIZE>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()), M, N, K);
}
"""

CPP_SOURCE = "void launch(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor);"

try:
    _mod = load_inline(
        name="fp4mfma_fixed", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_SOURCE],
        functions=["launch"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[fp4mfma] {e}")
    _OK = False


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    if not _OK:
        print("[GEMM] FALLBACK: using aiter.gemm_a4w4 (MFMA compilation failed)")
        import aiter
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh,
                               dtype=dtypes.bf16, bpreshuffle=True)
    print("[GEMM] CUSTOM: using FP4 MFMA kernel")

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)
    B_bytes = B_q.view(torch.uint8)
    _, Bsc = dynamic_mxfp4_quant(B.contiguous())
    Bs_bytes = Bsc[:N, :ks].contiguous().view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
    return C
