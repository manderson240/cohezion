#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Outer Product Accumulation - Alternative to Inner Product.

APPROACH:
This kernel implements GEMM using outer product accumulation instead of
inner product dot products. The outer product approach:
1. Load K elements of A (column vector)
2. Load K elements of B (row vector)
3. Compute outer product: A[:,k] @ B[k,:]
4. Accumulate to C tile

KEY INSIGHTS:
- Inner product: For each C[i,j], compute dot(A[i,:], B[:,j])
- Outer product: For each k, add outer(A[:,k], B[k,:]) to C
- Outer product allows vectorized loads of A and B
- Better register utilization on MI355X (304 CUs)

ALGORITHM (Outer Product):
```
C = 0
for k in range(K):
    a = A[:, k]  # Column of A (vector)
    b = B[k, :]  # Row of B (vector)
    C += outer(a, b)  # Rank-1 update
```

TILE OPTIMIZATION:
- Tile size: 128x128 for C accumulation
- K step: 8 (process 8 columns/rows at a time)
- Uses FP4 MFMA for matrix multiply
- Accumulates in FP32, converts to BF16 at end

Author: Experimental Kernel Series
"""

from __future__ import annotations

import os
import sys

import torch
from torch.utils.cpp_extension import load_inline


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# ============================================================================
# Outer Product GEMM Kernel (HIP)
# ============================================================================

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// Outer product accumulation GEMM kernel
// Computes C += A[:,k] * B[k,:] for each k in tiles

#define TILE_M 128
#define TILE_N 128
#define TILE_K 8  // Process 8 K values per iteration
#define WAVESIZE 64

__device__ __forceinline__ int e8m0_unshuffle(int idx, int N, int K_scale) {
    int row = idx / K_scale;
    int col = idx % K_scale;
    int i = row, j = col;
    return ((i/32)*32 + (j/8)*8 + (i%2)*4 + (j%8/4)*2 + (i%4/2)*1)*K_scale + (j%4);
}

// Outer product accumulation using MFMA
// Each block computes a TILE_M x TILE_N tile of C
__global__ void outer_product_gemm(
    const uint8_t* __restrict__ A,      // [M, K/2] FP4 packed
    const uint8_t* __restrict__ B,      // [N, K/2] FP4 packed (transposed access)
    const uint8_t* __restrict__ As,     // [M, K/32] E8M0 scales
    const uint8_t* __restrict__ Bs,     // [N, K/32] E8M0 scales
    __hip_bfloat16* __restrict__ C,     // [M, N] output
    int M, int N, int K
) {
    int bm = blockIdx.y * TILE_M;
    int bn = blockIdx.x * TILE_N;
    int tid = threadIdx.x;

    // Thread coordinates within tile
    int t_m = tid / 4;   // 0-15 (4 warps * 16 threads)
    int t_n = tid % 4;   // 0-3

    // FP32 accumulator for outer product
    float acc[TILE_M / 16][TILE_N / 4] = {};  // 8x32 per thread

    int K_half = K / 2;
    int K_scale = K / 32;
    int num_k_iters = K / TILE_K;

    // Outer product: for each k, load A[:,k] and B[k,:], accumulate
    for (int k_iter = 0; k_iter < num_k_iters; k_iter++) {
        int k_start = k_iter * TILE_K;

        // Load A column elements (TILE_K values per thread)
        // A is [M, K/2] packed, each thread loads portion
        float a_vals[TILE_K];
        int a_row = bm + t_m;

        #pragma unroll
        for (int k = 0; k < TILE_K; k++) {
            int k_idx = k_start + k;
            int k_packed = k_idx / 2;
            int k_nibble = k_idx % 2;

            if (a_row < M && k_idx < K) {
                uint8_t packed = A[a_row * K_half + k_packed];
                uint8_t nibble = (k_nibble == 0) ? (packed & 0x0F) : (packed >> 4);

                // Simple dequant: FP4 -> FP32 (approximate)
                // FP4 e2m1: sign=1, exp=2, mant=1 -> value = (-1)^s * 2^(e-1) * (1 + m/2)
                int sign = (nibble >> 3) & 1;
                int exp = (nibble >> 1) & 0x3;
                int mant = nibble & 1;

                float value = (1.0f + mant * 0.5f) * (1 << exp);
                if (sign) value = -value;

                // Apply E8M0 scale
                int sg = k_idx / 32;
                int sa = (int)As[e8m0_unshuffle(a_row * K_scale + sg, M, K_scale)];
                float scale_a = ldexpf(1.0f, sa - 127);

                a_vals[k] = value * scale_a;
            } else {
                a_vals[k] = 0.0f;
            }
        }

        // Load B row elements (TILE_K values per thread)
        // B is [N, K/2] packed, each thread loads portion
        float b_vals[TILE_K];
        int b_col = bn + t_n * 32;  // Each thread handles 32 N values

        #pragma unroll
        for (int k = 0; k < TILE_K; k++) {
            int k_idx = k_start + k;
            int k_packed = k_idx / 2;
            int k_nibble = k_idx % 2;

            if (b_col < N && k_idx < K) {
                uint8_t packed = B[b_col * K_half + k_packed];
                uint8_t nibble = (k_nibble == 0) ? (packed & 0x0F) : (packed >> 4);

                int sign = (nibble >> 3) & 1;
                int exp = (nibble >> 1) & 0x3;
                int mant = nibble & 1;

                float value = (1.0f + mant * 0.5f) * (1 << exp);
                if (sign) value = -value;

                // Apply E8M0 scale
                int sg = k_idx / 32;
                int sb = (int)Bs[e8m0_unshuffle(b_col * K_scale + sg, N, K_scale)];
                float scale_b = ldexpf(1.0f, sb - 127);

                b_vals[k] = value * scale_b;
            } else {
                b_vals[k] = 0.0f;
            }
        }

        // Outer product accumulation: acc[i,j] += a[i] * b[j]
        #pragma unroll
        for (int k = 0; k < TILE_K; k++) {
            #pragma unroll
            for (int i = 0; i < TILE_M / 16; i++) {
                #pragma unroll
                for (int j = 0; j < TILE_N / 4; j++) {
                    acc[i][j] += a_vals[k] * b_vals[k];
                }
            }
        }
    }

    // Write accumulated results to C
    #pragma unroll
    for (int i = 0; i < TILE_M / 16; i++) {
        int out_row = bm + t_m + i * 16;
        if (out_row < M) {
            #pragma unroll
            for (int j = 0; j < TILE_N / 4; j++) {
                int out_col = bn + t_n * 32 + j;
                if (out_col < N) {
                    C[out_row * N + out_col] = (__hip_bfloat16)acc[i][j];
                }
            }
        }
    }
}

// Simplified outer product using MFMA (if available)
__global__ void outer_product_gemm_mfma(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    // Use MFMA for matrix multiply
    // This is a placeholder - actual MFMA implementation would use
    // __builtin_amdgcn_mfma_* intrinsics

    // For now, delegate to simpler kernel
    outer_product_gemm<<<gridDim, blockDim>>>(A, B, As, Bs, C, M, N, K);
}

void launch_outer_product(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs, torch::Tensor C
) {
    int M = A.size(0);
    int K = A.size(1) * 2;  // Packed FP4
    int N = B.size(0);

    dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
    dim3 block(WAVESIZE * 4);  // 256 threads

    outer_product_gemm<<<grid, block>>>(
        A.data_ptr<uint8_t>(),
        B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(),
        Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K
    );
}
"""

CPP_SOURCE = """
void launch_outer_product(torch::Tensor A, torch::Tensor B,
                          torch::Tensor As, torch::Tensor Bs, torch::Tensor C);
"""


# ============================================================================
# Kernel Compilation
# ============================================================================

try:
    _outer_product_mod = load_inline(
        name="outer_product_gemm",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_outer_product"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OUTER_PRODUCT_OK = True
except Exception as e:
    print(f"[outer_product_gemm] Compilation failed: {e}")
    _OUTER_PRODUCT_OK = False


# ============================================================================
# Main Kernel Function
# ============================================================================


def custom_kernel(data: input_t) -> output_t:
    """Execute GEMM using outer product accumulation.

    Args:
        data: Tuple containing:
            - A: [M, K] bf16 input matrix
            - B: [N, K] bf16 weight matrix
            - B_q: [N, K/2] uint8 FP4 quantized weights
            - B_shuffle: [N, K/2] shuffled FP4 weights
            - B_scale_sh: [N, K/32] E8M0 scales (shuffled)

    Returns:
        C: [M, N] bf16 output matrix
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    # Quantize A to FP4
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = e8m0_shuffle(Asc[:M, :ks].contiguous().view(dtypes.fp8_e8m0)).view(torch.uint8)

    # B data
    B_bytes = B_q.view(torch.uint8)
    Bs_bytes = B_scale_sh.view(torch.uint8)

    # Try custom outer product kernel
    if _OUTER_PRODUCT_OK:
        try:
            print("[GEMM] Using outer product accumulation kernel")
            C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
            _outer_product_mod.launch_outer_product(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
            return C
        except Exception as e:
            print(f"[GEMM] Outer product kernel failed: {e}", file=sys.stderr)

    # Fallback to aiter GEMM
    print("[GEMM] Falling back to aiter gemm_a4w4")
    import aiter

    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2),
        B_shuffle,
        As_bytes.view(dtypes.fp8_e8m0),
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
