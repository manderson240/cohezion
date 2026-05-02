#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Cannon's Algorithm for Distributed-Style GEMM on Single GPU.

APPROACH:
This kernel implements Cannon's algorithm, a distributed matrix multiplication
algorithm, adapted for single-GPU execution with thread blocks as "nodes".

CANNON'S ALGORITHM:
1. Partition matrices into P x P grid of blocks
2. Each thread block owns C[i,j] = sum_k A[i,k] @ B[k,j]
3. Blocks rotate to access all required data
4. Accumulate partial results

SINGLE-GPU ADAPTATION:
- Use thread blocks as distributed nodes
- Shared memory as "local storage" per node
- Global memory for data rotation
- Synchronization points between rotations

KEY INSIGHTS:
- Cannon's minimizes communication in distributed systems
- On GPU: Maximizes data reuse in shared memory
- Rotation pattern ensures each block accesses all data
- Good for large matrices where data doesn't fit in L2

BLOCK PARTITION:
```
C = | C00 C01 |   A = | A00 A01 |   B = | B00 B01 |
    | C10 C11 |       | A10 A11 |       | B10 B11 |

C00 = A00@B00 + A01@B10
C01 = A00@B01 + A01@B11
...
```

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
# Cannon's Algorithm GEMM Kernel (HIP)
# ============================================================================

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// Cannon's algorithm for distributed-style GEMM
// Each block computes a sub-tile of C using rotating A and B blocks

#define BLOCK_M 64
#define BLOCK_N 64
#define BLOCK_K 64
#define WAVESIZE 64

__device__ __forceinline__ int e8m0_unshuffle(int idx, int N, int K_scale) {
    int row = idx / K_scale;
    int col = idx % K_scale;
    int i = row, j = col;
    return ((i/32)*32 + (j/8)*8 + (i%2)*4 + (j%8/4)*2 + (i%4/2)*1)*K_scale + (j%4);
}

// Cannon's algorithm kernel
// grid: (P, P) where P is grid dimension
// Each block computes C[i,j] = sum_k A[i,k] @ B[k,j]
__global__ void cannons_gemm(
    const uint8_t* __restrict__ A,      // [M, K/2] FP4
    const uint8_t* __restrict__ B,      // [N, K/2] FP4
    const uint8_t* __restrict__ As,     // [M, K/32] E8M0
    const uint8_t* __restrict__ Bs,     // [N, K/32] E8M0
    __hip_bfloat16* __restrict__ C,     // [M, N] output
    int M, int N, int K, int P          // P = sqrt(num_blocks)
) {
    // Block indices in P x P grid
    int bi = blockIdx.y;  // Row index
    int bj = blockIdx.x;  // Column index

    int tid = threadIdx.x;
    int lane = tid % WAVESIZE;
    int warp = tid / WAVESIZE;

    // Tile dimensions
    int tile_M = (M + P - 1) / P;
    int tile_N = (N + P - 1) / P;
    int tile_K = (K + P - 1) / P;

    // This block's tile of C
    int c_row_start = bi * tile_M;
    int c_col_start = bj * tile_N;

    // FP32 accumulator
    float acc[BLOCK_M / 4][BLOCK_N / 16] = {};  // Per-thread accumulator

    int K_half = K / 2;
    int K_scale = K / 32;

    // Cannon's algorithm: rotate through k dimension
    // Initial alignment: A[i,j] starts at k=(i+j)%P, B[i,j] at k=(i+j)%P
    for (int step = 0; step < P; step++) {
        // Determine which A and B blocks to load
        // A block comes from row bi, column (bi + bj + step) % P
        // B block comes from row (bi + bj + step) % P, column bj
        int a_col = (bi + bj + step) % P;
        int b_row = (bi + bj + step) % P;

        int a_row_start = bi * tile_M;
        int a_col_start = a_col * tile_K;
        int b_row_start = b_row * tile_N;
        int b_col_start = bj * tile_N;

        // Shared memory for A and B tiles
        __shared__ float smem_A[BLOCK_M][BLOCK_K / 2];  // Dequantized
        __shared__ float smem_B[BLOCK_K][BLOCK_N / 16]; // Per warp

        // Load A tile from global memory
        // Each thread loads a portion of the tile
        int a_local_rows = tile_M;
        int a_local_cols = tile_K / 2;  // FP4 packed

        for (int idx = tid; idx < a_local_rows * a_local_cols; idx += blockDim.x) {
            int ar = idx / a_local_cols;
            int ac = idx % a_local_cols;

            int global_a_row = a_row_start + ar;
            int global_a_col = a_col_start / 2 + ac;

            if (global_a_row < M && global_a_col < K_half) {
                uint8_t packed = A[global_a_row * K_half + global_a_col];
                uint8_t nibble1 = packed & 0x0F;
                uint8_t nibble2 = packed >> 4;

                // Dequantize FP4 nibbles
                auto dequant = [](uint8_t n) -> float {
                    int s = (n >> 3) & 1;
                    int e = (n >> 1) & 0x3;
                    int m = n & 1;
                    float v = (1.0f + m * 0.5f) * (1 << e);
                    return s ? -v : v;
                };

                // Apply E8M0 scale
                int sg = (a_col_start + ac * 2) / 32;
                int sa = (int)As[e8m0_unshuffle(global_a_row * K_scale + sg, M, K_scale)];
                float scale_a = ldexpf(1.0f, sa - 127);

                smem_A[ar][ac * 2] = dequant(nibble1) * scale_a;
                smem_A[ar][ac * 2 + 1] = dequant(nibble2) * scale_a;
            }
        }

        // Load B tile
        int b_local_rows = tile_K;
        int b_local_cols = tile_N / 2;  // FP4 packed

        // Simplified B loading (transposed access)
        for (int idx = tid; idx < b_local_rows * b_local_cols; idx += blockDim.x) {
            int br = idx / b_local_cols;
            int bc = idx % b_local_cols;

            int global_b_row = b_row_start + br / 2;  // B is transposed
            int global_b_col = b_col_start / 2 + bc;

            if (global_b_row < N && global_b_col < K_half) {
                uint8_t packed = B[global_b_row * K_half + global_b_col];
                uint8_t nibble = (br % 2 == 0) ? (packed & 0x0F) : (packed >> 4);

                auto dequant = [](uint8_t n) -> float {
                    int s = (n >> 3) & 1;
                    int e = (n >> 1) & 0x3;
                    int m = n & 1;
                    float v = (1.0f + m * 0.5f) * (1 << e);
                    return s ? -v : v;
                };

                int sg = (b_col_start + br) / 32;
                int sb = (int)Bs[e8m0_unshuffle(global_b_row * K_scale + sg, N, K_scale)];
                float scale_b = ldexpf(1.0f, sb - 127);

                // B is accessed transposed, so indices are swapped
                int smem_br = br;
                int smem_bc = bc * 2 + (br % 2);
                if (smem_br < BLOCK_K && smem_bc < tile_N) {
                    smem_B[smem_br][smem_bc] = dequant(nibble) * scale_b;
                }
            }
        }

        __syncthreads();

        // Compute partial C tile: A_tile @ B_tile
        // Each thread computes a portion
        int thread_m = tid / 16;
        int thread_n = tid % 16;

        #pragma unroll
        for (int m = 0; m < BLOCK_M / 4; m++) {
            int smem_m = thread_m + m * 4;
            if (smem_m >= tile_M) break;

            #pragma unroll
            for (int n = 0; n < BLOCK_N / 16; n++) {
                int smem_n = thread_n + n * 16;
                if (smem_n >= tile_N) break;

                // Dot product over K
                float dot = 0.0f;
                #pragma unroll
                for (int k = 0; k < tile_K && k < BLOCK_K; k++) {
                    dot += smem_A[smem_m][k] * smem_B[k][smem_n];
                }
                acc[m][n] += dot;
            }
        }

        __syncthreads();
    }

    // Write results to C
    for (int m = 0; m < BLOCK_M / 4; m++) {
        int global_m = c_row_start + tid / 16 + m * 4;
        if (global_m >= M) break;

        for (int n = 0; n < BLOCK_N / 16; n++) {
            int global_n = c_col_start + (tid % 16) + n * 16;
            if (global_n >= N) break;

            C[global_m * N + global_n] = (__hip_bfloat16)acc[m][n];
        }
    }
}

void launch_cannons(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs, torch::Tensor C,
    int P
) {
    int M = A.size(0);
    int K = A.size(1) * 2;
    int N = B.size(0);

    dim3 grid(P, P);
    dim3 block(256);  // 4 warps per block

    cannons_gemm<<<grid, block>>>(
        A.data_ptr<uint8_t>(),
        B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(),
        Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K, P
    );
}
"""

CPP_SOURCE = """
void launch_cannons(torch::Tensor A, torch::Tensor B,
                    torch::Tensor As, torch::Tensor Bs, torch::Tensor C, int P);
"""


# ============================================================================
# Kernel Compilation
# ============================================================================

try:
    _cannons_mod = load_inline(
        name="cannons_gemm",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_cannons"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _CANNONS_OK = True
except Exception as e:
    print(f"[cannons_gemm] Compilation failed: {e}")
    _CANNONS_OK = False


# ============================================================================
# Helper Functions
# ============================================================================


def compute_grid_dim(M: int, N: int, target_blocks: int = 256) -> int:
    """Compute grid dimension P for Cannon's algorithm.

    We want P x P blocks covering the matrix.
    P is chosen to:
    1. Cover the matrix: P * BLOCK_M >= M and P * BLOCK_N >= N
    2. Use target number of blocks: P * P ≈ target_blocks

    Args:
        M: Number of rows
        N: Number of columns
        target_blocks: Target number of thread blocks

    Returns:
        Grid dimension P
    """
    BLOCK_M = 64
    BLOCK_N = 64

    # Minimum P to cover the matrix
    P_min_m = (M + BLOCK_M - 1) // BLOCK_M
    P_min_n = (N + BLOCK_N - 1) // BLOCK_N
    P_min = max(P_min_m, P_min_n, 1)

    # Ideal P based on target blocks
    P_ideal = int(target_blocks**0.5)

    # Use the larger of the two (must cover matrix)
    P = max(P_min, P_ideal)

    # Round up to power of 2 for simpler indexing
    P = 1 << (P - 1).bit_length()

    # Cap at reasonable max
    P = min(P, 32)

    return max(P, 2)  # Minimum 2x2 grid


# ============================================================================
# Main Kernel Function
# ============================================================================


def custom_kernel(data: input_t) -> output_t:
    """Execute GEMM using Cannon's algorithm.

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

    # Determine grid dimension
    P = compute_grid_dim(M, N, target_blocks=256)

    # Try Cannon's algorithm for sufficiently large matrices
    if _CANNONS_OK and M >= 128 and N >= 128 and P >= 2:
        try:
            print(f"[GEMM] Using Cannon's algorithm with {P}x{P} grid")
            C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
            _cannons_mod.launch_cannons(A_bytes, B_bytes, As_bytes, Bs_bytes, C, P)
            return C
        except Exception as e:
            print(f"[GEMM] Cannon's algorithm failed: {e}", file=sys.stderr)

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
