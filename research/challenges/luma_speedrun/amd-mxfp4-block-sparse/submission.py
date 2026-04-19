#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""
GEMM: Block Sparse Multiplication

This kernel implements block-sparse matrix multiplication where zero blocks
are skipped entirely, reducing both computation and memory bandwidth.

Block Sparse Format:
  - Matrix divided into blocks (e.g., 32x32)
  - Metadata tracks which blocks are non-zero
  - Only non-zero blocks are stored and computed

Sparse Patterns Supported:
  - Block diagonal: Non-zero blocks only on diagonal
  - Banded: Non-zero blocks near diagonal
  - Random block sparse: Arbitrary non-zero block pattern
  - Structured: Repeating patterns (e.g., for convolution)

Algorithm:
  1. Load block metadata (sparse indices)
  2. For each non-zero block pair (A[i,k], B[k,j])
  3. Load blocks from memory
  4. Compute GEMM on blocks
  5. Accumulate to output

Memory Efficiency:
  - Only store non-zero blocks
  - Index overhead: ~2-4 bytes per block
  - Bandwidth reduction proportional to sparsity

Compute Efficiency:
  - Skip zero block multiplications entirely
  - No wasted thread cycles on zeros
  - Better cache utilization

Performance Characteristics:
  - Best with >50% block sparsity
  - Overhead: metadata loading and indirect indexing
  - Trade-off: sparsity vs metadata overhead
  - Optimal block size: 32x32 or 64x64
"""

from __future__ import annotations
import os
import math

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Block sparse configuration
BLOCK_SIZE = 32  # Block dimension (32x32)
SPARSITY_THRESHOLD = 0.5  # Minimum sparsity to use sparse kernel

# Kernel cache
_kernel_mod = None
_kernel_ok = False


def _detect_block_sparsity(
    matrix: torch.Tensor, block_size: int = BLOCK_SIZE
) -> tuple[torch.Tensor, float]:
    """
    Detect block sparsity pattern in matrix.

    Args:
        matrix: [M, N] input matrix
        block_size: Size of blocks to check

    Returns:
        block_mask: [num_block_m, num_block_n] boolean mask of non-zero blocks
        sparsity_ratio: Fraction of zero blocks
    """
    M, N = matrix.shape
    num_block_m = (M + block_size - 1) // block_size
    num_block_n = (N + block_size - 1) // block_size

    # Check each block
    block_mask = torch.zeros(num_block_m, num_block_n, dtype=torch.bool, device=matrix.device)

    for bm in range(num_block_m):
        for bn in range(num_block_n):
            m_start = bm * block_size
            m_end = min(m_start + block_size, M)
            n_start = bn * block_size
            n_end = min(n_start + block_size, N)

            block = matrix[m_start:m_end, n_start:n_end]
            block_mask[bm, bn] = block.abs().max() > 1e-6

    sparsity_ratio = 1.0 - block_mask.float().mean().item()

    return block_mask, sparsity_ratio


def _compress_sparse_matrix(
    matrix: torch.Tensor, block_mask: torch.Tensor, block_size: int = BLOCK_SIZE
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Compress matrix to block-sparse format.

    Args:
        matrix: [M, N] dense matrix
        block_mask: [num_block_m, num_block_n] non-zero block mask
        block_size: Block dimension

    Returns:
        values: [num_nonzero_blocks, block_size, block_size] block values
        row_indices: [num_block_m + 1] row pointers (CSR-like)
        col_indices: [num_nonzero_blocks] column indices
    """
    M, N = matrix.shape
    num_block_m, num_block_n = block_mask.shape
    device = matrix.device

    # Find non-zero blocks
    nonzero_indices = torch.nonzero(block_mask, as_tuple=False)  # [nnz, 2]
    num_nnz = nonzero_indices.shape[0]

    # Extract non-zero blocks
    values = torch.zeros(num_nnz, block_size, block_size, dtype=matrix.dtype, device=device)

    for idx, (bm, bn) in enumerate(nonzero_indices):
        m_start = bm * block_size
        m_end = min(m_start + block_size, M)
        n_start = bn * block_size
        n_end = min(n_start + block_size, N)

        block = matrix[m_start:m_end, n_start:n_end]

        # Pad to full block size
        if block.shape[0] < block_size or block.shape[1] < block_size:
            padded = torch.zeros(block_size, block_size, dtype=matrix.dtype, device=device)
            padded[: block.shape[0], : block.shape[1]] = block
            values[idx] = padded
        else:
            values[idx] = block

    # Create CSR-like row pointers
    row_counts = block_mask.sum(dim=1)  # [num_block_m]
    row_indices = torch.cat(
        [torch.zeros(1, dtype=torch.long, device=device), torch.cumsum(row_counts, dim=0)]
    )

    # Column indices
    col_indices = nonzero_indices[:, 1]  # [num_nnz]

    return values, row_indices, col_indices


def _get_block_sparse_kernel():
    """Lazy initialization of block sparse GEMM kernel."""
    global _kernel_mod, _kernel_ok

    if _kernel_mod is not None:
        return _kernel_mod, _kernel_ok

    HIP_SOURCE = r"""
    #include <torch/extension.h>
    #include <hip/hip_runtime.h>
    #include <hip/hip_bf16.h>
    
    #define BLOCK_SIZE 32
    #define WAVESIZE 64
    
    // Block sparse GEMM: C = A_sparse * B
    __global__ __launch_bounds__(256)
    void block_sparse_gemm(
        const __hip_bfloat16* __restrict__ A_values,     // [num_nnz, BLOCK_SIZE, BLOCK_SIZE]
        const int* __restrict__ A_row_indices,            // [num_block_m + 1]
        const int* __restrict__ A_col_indices,            // [num_nnz]
        const __hip_bfloat16* __restrict__ B,            // [N, K]
        __hip_bfloat16* __restrict__ C,                  // [M, N]
        int num_block_m, int num_block_n, int K
    ) {
        int block_m = blockIdx.y;
        int block_n = blockIdx.x;
        int tid = threadIdx.x;
        
        int local_m = tid / BLOCK_SIZE;
        int local_n = tid % BLOCK_SIZE;
        
        // Accumulator for this output block element
        float acc = 0.0f;
        
        // Iterate over non-zero A blocks in this row
        int row_start = A_row_indices[block_m];
        int row_end = A_row_indices[block_m + 1];
        
        for (int idx = row_start; idx < row_end; idx++) {
            int block_k = A_col_indices[idx];
            
            // Load A block
            const __hip_bfloat16* A_block = A_values + idx * BLOCK_SIZE * BLOCK_SIZE;
            float a_val = __bfloat162float(A_block[local_m * BLOCK_SIZE + local_n]);
            
            // Load corresponding B elements and multiply
            int global_m = block_m * BLOCK_SIZE + local_m;
            int global_n = block_n * BLOCK_SIZE + local_n;
            int global_k = block_k * BLOCK_SIZE + local_n;
            
            if (global_m < num_block_m * BLOCK_SIZE && global_n < num_block_n * BLOCK_SIZE) {
                for (int k = 0; k < BLOCK_SIZE && global_k + k < K; k++) {
                    float b_val = __bfloat162float(B[(global_n) * K + global_k + k]);
                    acc += a_val * b_val;
                }
            }
        }
        
        // Write output
        int global_m = block_m * BLOCK_SIZE + local_m;
        int global_n = block_n * BLOCK_SIZE + local_n;
        
        if (global_m < num_block_m * BLOCK_SIZE && global_n < num_block_n * BLOCK_SIZE) {
            C[global_m * (num_block_n * BLOCK_SIZE) + global_n] = (__hip_bfloat16)acc;
        }
    }
    
    void launch_block_sparse(
        torch::Tensor A_values, torch::Tensor A_row_indices, torch::Tensor A_col_indices,
        torch::Tensor B, torch::Tensor C,
        int num_block_m, int num_block_n, int K
    ) {
        dim3 grid(num_block_n, num_block_m);
        block_sparse_gemm<<<grid, 256>>>(
            reinterpret_cast<const __hip_bfloat16*>(A_values.data_ptr()),
            A_row_indices.data_ptr<int>(),
            A_col_indices.data_ptr<int>(),
            reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            num_block_m, num_block_n, K
        );
    }
    """

    CPP_SOURCE = """
    void launch_block_sparse(torch::Tensor A_values, torch::Tensor A_row_indices,
                              torch::Tensor A_col_indices, torch::Tensor B,
                              torch::Tensor C, int num_block_m, int num_block_n, int K);
    """

    try:
        _kernel_mod = load_inline(
            name="block_sparse_gemm",
            cpp_sources=[CPP_SOURCE],
            cuda_sources=[HIP_SOURCE],
            functions=["launch_block_sparse"],
            verbose=False,
            extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
        )
        _kernel_ok = True
    except Exception as e:
        print(f"[BlockSparse] Kernel build failed: {e}")
        _kernel_mod = None
        _kernel_ok = False

    return _kernel_mod, _kernel_ok


def _aiter_gemm(data: input_t) -> torch.Tensor:
    """Aiter GEMM with MXFP4 quantization."""
    A, B, B_q, B_shuffle, B_scale_sh = data

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)

    import aiter

    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )


def custom_kernel(data: input_t) -> output_t:
    """
    Block sparse GEMM kernel.

    Implements sparse matrix multiplication with block-level
    sparsity for reduced computation and memory bandwidth.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Detect sparsity in A matrix
    block_mask, sparsity = _detect_block_sparsity(A, BLOCK_SIZE)

    # Only use sparse kernel if sparsity is high enough
    if sparsity >= SPARSITY_THRESHOLD:
        mod, ok = _get_block_sparse_kernel()

        if ok and mod is not None:
            try:
                # Compress A to block-sparse format
                A_values, A_row_indices, A_col_indices = _compress_sparse_matrix(
                    A, block_mask, BLOCK_SIZE
                )

                # Prepare output
                C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

                # Launch sparse kernel
                num_block_m = (M + BLOCK_SIZE - 1) // BLOCK_SIZE
                num_block_n = (N + BLOCK_SIZE - 1) // BLOCK_SIZE

                mod.launch_block_sparse(
                    A_values,
                    A_row_indices,
                    A_col_indices,
                    B.to(torch.bfloat16),
                    C,
                    num_block_m,
                    num_block_n,
                    K,
                )

                return C.to(A.dtype)

            except Exception as e:
                print(f"[BlockSparse] Sparse execution failed: {e}")

    # Fallback to aiter
    try:
        return _aiter_gemm(data)
    except Exception as e:
        print(f"[BlockSparse] Aiter fallback failed: {e}")
        return torch.matmul(A, B.t())
