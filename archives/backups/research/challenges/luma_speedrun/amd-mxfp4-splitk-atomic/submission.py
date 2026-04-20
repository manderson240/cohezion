#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G4: Split-K GEMM with atomic accumulation.

Novel approach: Parallelize K dimension across CUs with atomic add for accumulation.

Standard GEMM: Each output element C[i,j] = sum_k A[i,k] * B[j,k]
- K loop is sequential within each thread

Split-K GEMM: Split K into chunks, compute partial sums in parallel, accumulate with atomics
- Each block computes partial sum for a K chunk
- Final accumulation uses atomicAdd for correctness

Benefits:
- Better occupancy when M*N is small but K is large
- Parallel reduction across K dimension
- Can saturate more CUs for "tall and skinny" matrices

Implementation details:
- Uses float32 for accumulation precision
- Atomic add to output tensor
- Configurable split factor based on K size

Best for: Large K with moderate M,N (where standard GEMM has low occupancy)
"""

from __future__ import annotations
import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# Import aiter for fallback and quantization
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
import aiter

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define TILE_M 32
#define TILE_N 32
#define TILE_K 64
#define WAVESIZE 64

// Split-K GEMM kernel with atomic accumulation
// Each block handles a K-split of the output tile
__global__ void splitk_gemm_atomic(
    const __hip_bfloat16* __restrict__ A,   // [M, K] row-major
    const __hip_bfloat16* __restrict__ B,   // [N, K] row-major
    __hip_bfloat16* __restrict__ C,       // [M, N] row-major (atomic accumulation)
    int M, int N, int K,
    int k_split_id, int num_k_splits
) {
    int tid = threadIdx.x;
    int lane = tid % WAVESIZE;
    int wave = tid / WAVESIZE;

    // Compute output tile this block is responsible for
    int tile_m = blockIdx.y;
    int tile_n = blockIdx.x;

    int m_start = tile_m * TILE_M;
    int n_start = tile_n * TILE_N;

    // K range for this split
    int k_per_split = (K + num_k_splits - 1) / num_k_splits;
    int k_start = k_split_id * k_per_split;
    int k_end = min(k_start + k_per_split, K);

    // Accumulators for this thread's output elements
    float acc[TILE_M * TILE_N / WAVESIZE] = {0.0f};

    // Each thread computes a subset of the output tile
    // Distribute (TILE_M * TILE_N) outputs across WAVESIZE threads
    int outputs_per_thread = (TILE_M * TILE_N + WAVESIZE - 1) / WAVESIZE;

    // Iterate over K range for this split
    for (int k = k_start; k < k_end; k += TILE_K) {
        int k_end_local = min(k + TILE_K, k_end);

        // Load A tile: [TILE_M, TILE_K]
        __shared__ __hip_bfloat16 A_shared[TILE_M * TILE_K];
        // Load B tile: [TILE_N, TILE_K]
        __shared__ __hip_bfloat16 B_shared[TILE_N * TILE_K];

        // Cooperative load A
        for (int i = tid; i < TILE_M * TILE_K; i += blockDim.x) {
            int row = i / TILE_K;
            int col = i % TILE_K;
            int global_k = k + col;
            int global_m = m_start + row;

            if (global_m < M && global_k < K) {
                A_shared[i] = A[global_m * K + global_k];
            } else {
                A_shared[i] = __float2bfloat16_rn(0.0f);
            }
        }

        // Cooperative load B
        for (int i = tid; i < TILE_N * TILE_K; i += blockDim.x) {
            int row = i / TILE_K;
            int col = i % TILE_K;
            int global_k = k + col;
            int global_n = n_start + row;

            if (global_n < N && global_k < K) {
                B_shared[i] = B[global_n * K + global_k];
            } else {
                B_shared[i] = __float2bfloat16_rn(0.0f);
            }
        }

        __syncthreads();

        // Compute partial matmul for this K tile
        // Each thread handles outputs_per_thread output elements
        for (int out_idx = lane; out_idx < TILE_M * TILE_N; out_idx += WAVESIZE) {
            int local_m = out_idx / TILE_N;
            int local_n = out_idx % TILE_N;

            float sum = 0.0f;
            for (int kk = 0; kk < (k_end_local - k); kk++) {
                float a_val = __bfloat162float(A_shared[local_m * TILE_K + kk]);
                float b_val = __bfloat162float(B_shared[local_n * TILE_K + kk]);
                sum += a_val * b_val;
            }

            int acc_idx = out_idx / WAVESIZE;
            if (acc_idx < outputs_per_thread) {
                acc[acc_idx] += sum;
            }
        }

        __syncthreads();
    }

    // Accumulate to output with atomics
    // Only threads with valid outputs participate
    for (int out_idx = lane; out_idx < TILE_M * TILE_N; out_idx += WAVESIZE) {
        int local_m = out_idx / TILE_N;
        int local_n = out_idx % TILE_N;

        int global_m = m_start + local_m;
        int global_n = n_start + local_n;

        if (global_m < M && global_n < N) {
            int acc_idx = out_idx / WAVESIZE;
            if (acc_idx < outputs_per_thread) {
                float val = acc[acc_idx];

                // Atomic add to global output
                // For bfloat16, we need to convert to float, atomic add, convert back
                // Or use atomicAdd on float32 accumulator then convert

                // Since ROCm doesn't have atomicAdd for bfloat16 directly,
                // we use a workaround: store to float32 accumulator, then convert
                int* C_int = reinterpret_cast<int*>(C);
                int old_val, new_val;
                do {
                    old_val = C_int[global_m * N + global_n];
                    float old_float = __bfloat162float(*reinterpret_cast<__hip_bfloat16*>(&old_val));
                    float new_float = old_float + val;
                    new_val = *reinterpret_cast<int*>(&new_float);
                } while (atomicCAS(&C_int[global_m * N + global_n], old_val, new_val) != old_val);
            }
        }
    }
}

// Initialize output to zero before atomic accumulation
__global__ void zero_fill(
    __hip_bfloat16* __restrict__ C,
    int M, int N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int total = M * N;
    if (idx < total) {
        C[idx] = __float2bfloat16_rn(0.0f);
    }
}

void launch_splitk_gemm(
    torch::Tensor A, torch::Tensor B, torch::Tensor C,
    int num_k_splits
) {
    int M = A.size(0);
    int K = A.size(1);
    int N = B.size(0);

    // Zero output first
    int total_elems = M * N;
    zero_fill<<<(total_elems + 255) / 256, 256>>>(
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()), M, N);

    // Launch split-k kernels
    dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
    dim3 block(256);

    for (int split_id = 0; split_id < num_k_splits; split_id++) {
        splitk_gemm_atomic<<<grid, block>>>(
            reinterpret_cast<const __hip_bfloat16*>(A.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            M, N, K, split_id, num_k_splits);
    }
}
"""

CPP_SOURCE = """
void launch_splitk_gemm(torch::Tensor A, torch::Tensor B, torch::Tensor C, int num_k_splits);
"""

# Compile kernel
try:
    _mod = load_inline(
        name="splitk_gemm",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_splitk_gemm"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _SPLITK_OK = True
except Exception as e:
    print(f"[splitk] Compilation failed: {e}")
    _SPLITK_OK = False


def _choose_num_k_splits(K):
    """Choose number of K splits based on K size."""
    if K <= 256:
        return 1
    if K <= 1024:
        return 2
    if K <= 4096:
        return 4
    if K <= 16384:
        return 8
    return 16


def custom_kernel(data: input_t) -> output_t:
    """Split-K GEMM with atomic accumulation.

    Splits the K dimension across multiple thread blocks,
    computing partial sums that are accumulated atomically.

    Falls back to aiter.gemm_a4w4 on any error.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Determine if split-K is beneficial
    num_k_splits = _choose_num_k_splits(K)

    if num_k_splits == 1 or not _SPLITK_OK:
        # Not beneficial or kernel unavailable: use standard GEMM
        if num_k_splits == 1:
            print("[splitk] K too small for splitting, using standard")
        else:
            print("[splitk] Kernel unavailable, using standard")

        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )

    # Try split-K GEMM
    try:
        print(f"[splitk] Using split-K with {num_k_splits} splits")

        # Convert to bfloat16 for computation
        # In production, this would use FP4 MFMA directly
        A_bf16 = A.to(torch.bfloat16)
        B_bf16 = B.to(torch.bfloat16)

        # Allocate output
        C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

        # Launch split-K kernel
        _mod.launch_splitk_gemm(A_bf16, B_bf16, C, num_k_splits)

        return C

    except Exception as e:
        print(f"[splitk] Runtime error: {e}, falling back to aiter")
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )
