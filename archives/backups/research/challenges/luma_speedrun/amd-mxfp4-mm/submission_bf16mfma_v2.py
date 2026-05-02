#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: BF16 MFMA with CORRECTED output mapping.

FIX: Output mapping is c_reg[j] → C[(tid/16)*4 + j][tid % 16]
NOT c_reg[j] → C[tid%16][(tid/16)*4 + j] (which was transposed!)

- 64 threads per 16×16 tile
- K tiles of 128 FP4 → 8 MFMA calls per sync
- FP4→BF16 dequant with scale in LDS
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

typedef short v4s __attribute__((ext_vector_type(4)));
typedef float v4f __attribute__((ext_vector_type(4)));

#define TILE_M 16
#define TILE_N 16
#define TILE_K_FP4 128
#define TILE_K_BF16 16
#define NUM_MFMA 8
#define WAVESIZE 64
#define SCALE_GROUP 32

__constant__ float FP4_LUT[16] = {
    0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
    -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f
};

__device__ __forceinline__ float e8m0_f(uint8_t v) {
    return (v == 0 || v == 255) ? 0.0f : exp2f((float)((int)v - 127));
}

__device__ __forceinline__ v4f bf16_mfma(v4s a, v4s b, v4f c) {
    return __builtin_amdgcn_mfma_f32_16x16x16bf16_1k(a, b, c, 0, 0, 0);
}

__global__ void mxfp4_gemm_bf16mfma(
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
    int K_scale = K / SCALE_GROUP;
    int num_k_tiles = K / TILE_K_FP4;

    // LDS: BF16 tiles [16][128] = 4KB each
    __shared__ __hip_bfloat16 lds_a[TILE_M * TILE_K_FP4];
    __shared__ __hip_bfloat16 lds_b[TILE_N * TILE_K_FP4];

    v4f c_reg = {0.0f, 0.0f, 0.0f, 0.0f};

    for (int kt = 0; kt < num_k_tiles; kt++) {
        int fp4_off = kt * (TILE_K_FP4 / 2);

        // Dequant FP4→BF16 with scale, store to LDS
        for (int idx = tid; idx < TILE_M * TILE_K_FP4; idx += WAVESIZE) {
            int row = idx / TILE_K_FP4;
            int k = idx % TILE_K_FP4;
            int gr = bm + row;
            if (gr >= M) { lds_a[idx] = (__hip_bfloat16)0.0f; continue; }
            int byte_idx = k / 2;
            int nibble = k % 2;
            uint8_t packed = A[gr * K_half + fp4_off + byte_idx];
            uint8_t fp4_val = nibble ? ((packed >> 4) & 0xF) : (packed & 0xF);
            int sg = (kt * (TILE_K_FP4 / SCALE_GROUP)) + (k / SCALE_GROUP);
            float scale = (sg < K_scale) ? e8m0_f(As[gr * K_scale + sg]) : 0.0f;
            lds_a[idx] = (__hip_bfloat16)(FP4_LUT[fp4_val] * scale);
        }

        for (int idx = tid; idx < TILE_N * TILE_K_FP4; idx += WAVESIZE) {
            int row = idx / TILE_K_FP4;
            int k = idx % TILE_K_FP4;
            int gr = bn + row;
            if (gr >= N) { lds_b[idx] = (__hip_bfloat16)0.0f; continue; }
            int byte_idx = k / 2;
            int nibble = k % 2;
            uint8_t packed = B[gr * K_half + fp4_off + byte_idx];
            uint8_t fp4_val = nibble ? ((packed >> 4) & 0xF) : (packed & 0xF);
            int sg = (kt * (TILE_K_FP4 / SCALE_GROUP)) + (k / SCALE_GROUP);
            float scale = (sg < K_scale) ? e8m0_f(Bs[gr * K_scale + sg]) : 0.0f;
            lds_b[idx] = (__hip_bfloat16)(FP4_LUT[fp4_val] * scale);
        }

        __syncthreads();

        // 8 MFMA calls (K=16 each)
        for (int mk = 0; mk < NUM_MFMA; mk++) {
            int k_off = mk * TILE_K_BF16;

            // CDNA input mapping: thread t reads row tid%16, K segment (tid/16)*4
            int a_row = tid % 16;
            int a_k = k_off + (tid / 16) * 4;
            v4s a_reg = *reinterpret_cast<v4s*>(&lds_a[a_row * TILE_K_FP4 + a_k]);

            int b_row = tid % 16;
            int b_k = k_off + (tid / 16) * 4;
            v4s b_reg = *reinterpret_cast<v4s*>(&lds_b[b_row * TILE_K_FP4 + b_k]);

            c_reg = bf16_mfma(a_reg, b_reg, c_reg);
        }

        __syncthreads();
    }

    // Handle K remainder
    int remaining = K - num_k_tiles * TILE_K_FP4;
    if (remaining > 0) {
        int fp4_off = num_k_tiles * (TILE_K_FP4 / 2);
        for (int idx = tid; idx < TILE_M * TILE_K_FP4; idx += WAVESIZE)
            lds_a[idx] = (__hip_bfloat16)0.0f;
        for (int idx = tid; idx < TILE_N * TILE_K_FP4; idx += WAVESIZE)
            lds_b[idx] = (__hip_bfloat16)0.0f;
        __syncthreads();
        for (int idx = tid; idx < TILE_M * remaining; idx += WAVESIZE) {
            int row = idx / remaining;
            int k = idx % remaining;
            int gr = bm + row;
            if (gr >= M) continue;
            int byte_idx = k / 2, nibble = k % 2;
            uint8_t packed = A[gr * K_half + fp4_off + byte_idx];
            uint8_t fp4_val = nibble ? ((packed >> 4) & 0xF) : (packed & 0xF);
            int sg = (num_k_tiles * (TILE_K_FP4 / SCALE_GROUP)) + (k / SCALE_GROUP);
            float scale = (sg < K_scale) ? e8m0_f(As[gr * K_scale + sg]) : 0.0f;
            lds_a[row * TILE_K_FP4 + k] = (__hip_bfloat16)(FP4_LUT[fp4_val] * scale);
        }
        for (int idx = tid; idx < TILE_N * remaining; idx += WAVESIZE) {
            int row = idx / remaining;
            int k = idx % remaining;
            int gr = bn + row;
            if (gr >= N) continue;
            int byte_idx = k / 2, nibble = k % 2;
            uint8_t packed = B[gr * K_half + fp4_off + byte_idx];
            uint8_t fp4_val = nibble ? ((packed >> 4) & 0xF) : (packed & 0xF);
            int sg = (num_k_tiles * (TILE_K_FP4 / SCALE_GROUP)) + (k / SCALE_GROUP);
            float scale = (sg < K_scale) ? e8m0_f(Bs[gr * K_scale + sg]) : 0.0f;
            lds_b[row * TILE_K_FP4 + k] = (__hip_bfloat16)(FP4_LUT[fp4_val] * scale);
        }
        __syncthreads();
        int nm = (remaining + TILE_K_BF16 - 1) / TILE_K_BF16;
        for (int mk = 0; mk < nm; mk++) {
            int k_off = mk * TILE_K_BF16;
            v4s a_reg = *reinterpret_cast<v4s*>(&lds_a[(tid%16)*TILE_K_FP4 + k_off + (tid/16)*4]);
            v4s b_reg = *reinterpret_cast<v4s*>(&lds_b[(tid%16)*TILE_K_FP4 + k_off + (tid/16)*4]);
            c_reg = bf16_mfma(a_reg, b_reg, c_reg);
        }
        __syncthreads();
    }

    // CORRECTED output mapping: c_reg[j] → C[(tid/16)*4 + j][tid % 16]
    // This is 4 consecutive ROWS at a single COLUMN
    int out_col = bn + (tid % 16);
    int out_row_base = bm + (tid / 16) * 4;

    if (out_col < N) {
        for (int j = 0; j < 4; j++) {
            int out_row = out_row_base + j;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(((float*)&c_reg)[j]);
            }
        }
    }
}

void mxfp4_gemm_launch(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C
) {
    int M = A.size(0);
    int K = A.size(1) * 2;
    int N = B.size(0);
    dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
    mxfp4_gemm_bf16mfma<<<grid, WAVESIZE>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""

CPP_SOURCE = "void mxfp4_gemm_launch(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor);"

try:
    _mod = load_inline(
        name="bf16mfma_v2",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["mxfp4_gemm_launch"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[bf16mfma_v2] {e}")
    _OK = False


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
    _, Bsc = dynamic_mxfp4_quant(B.contiguous())
    Bs_bytes = Bsc[:N, :ks].contiguous().view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.mxfp4_gemm_launch(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
    return C
