#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""
GEMM: Strassen Fast Multiplication

This kernel implements Strassen's algorithm for fast matrix multiplication.
Strassen reduces the complexity from O(n^3) to O(n^2.81) by trading
multiplications for additions using a clever divide-and-conquer approach.

Algorithm:
For C = A * B where all are NxN matrices:

Strassen divides matrices into quadrants:
  A = [A11 A12]    B = [B11 B12]    C = [C11 C12]
      [A21 A22]        [B21 B22]        [C21 C22]

Computes 7 products (M1-M7) instead of 8:
  M1 = (A11 + A22) * (B11 + B22)
  M2 = (A21 + A22) * B11
  M3 = A11 * (B12 - B22)
  M4 = A22 * (B21 - B11)
  M5 = (A11 + A12) * B22
  M6 = (A21 - A11) * (B11 + B12)
  M7 = (A12 - A22) * (B21 + B22)

Then combines:
  C11 = M1 + M4 - M5 + M7
  C12 = M3 + M5
  C21 = M2 + M4
  C22 = M1 - M2 + M3 + M6

Key Properties:
- Recursive: applies to sub-matrices until base case
- 7 multiplications vs 8 for naive (12.5% reduction)
- 18 additions vs 4 for naive
- Crossover point: additions overhead vs multiplication savings
- On GPUs: fewer memory-bound operations can outweigh arithmetic gains

Implementation Strategy:
1. Pad matrices to power-of-2 or multiple of 64 for alignment
2. Recursive decomposition with configurable base case
3. Fall back to high-performance GEMM for small tiles
4. Parallel sub-problem execution via kernel fusion

Performance Characteristics:
- Best for large square matrices
- Memory bandwidth bound: fewer total memory accesses
- Trade-off: more kernel launches vs fewer operations
- Modern GPUs: need to balance with cache-friendly blocking
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

# Strassen configuration
STRASSEN_MIN_SIZE = 64  # Minimum size to apply Strassen (below: use standard GEMM)
STRASSEN_BASE_SIZE = 32  # Base case for recursion
STRASSEN_PAD_ALIGN = 64  # Pad to this alignment

# Cache for kernel module
_kernel_mod = None
_kernel_ok = False


def _get_strassen_kernel():
    """Lazy initialization of Strassen GEMM kernel."""
    global _kernel_mod, _kernel_ok

    if _kernel_mod is not None:
        return _kernel_mod, _kernel_ok

    HIP_SOURCE = r"""
    #include <torch/extension.h>
    #include <hip/hip_runtime.h>
    #include <hip/hip_bf16.h>
    
    #define BLOCK_SIZE 64
    
    // Add two matrices: C = A + B
    __global__ void mat_add(
        const __hip_bfloat16* A,
        const __hip_bfloat16* B,
        __hip_bfloat16* C,
        int n
    ) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        int total = n * n;
        if (idx < total) {
            C[idx] = (__hip_bfloat16)(
                __bfloat162float(A[idx]) + __bfloat162float(B[idx])
            );
        }
    }
    
    // Subtract two matrices: C = A - B
    __global__ void mat_sub(
        const __hip_bfloat16* A,
        const __hip_bfloat16* B,
        __hip_bfloat16* C,
        int n
    ) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        int total = n * n;
        if (idx < total) {
            C[idx] = (__hip_bfloat16)(
                __bfloat162float(A[idx]) - __bfloat162float(B[idx])
            );
        }
    }
    
    // Naive matrix multiply: C = A * B
    // For small base case in Strassen recursion
    __global__ void mat_mul_base(
        const __hip_bfloat16* A,
        const __hip_bfloat16* B,
        __hip_bfloat16* C,
        int n
    ) {
        int row = blockIdx.y * blockDim.y + threadIdx.y;
        int col = blockIdx.x * blockDim.x + threadIdx.x;
        
        if (row < n && col < n) {
            float sum = 0.0f;
            for (int k = 0; k < n; k++) {
                sum += __bfloat162float(A[row * n + k]) *
                       __bfloat162float(B[k * n + col]);
            }
            C[row * n + col] = (__hip_bfloat16)sum;
        }
    }
    
    // Strassen combination kernel: compute C quadrants from M1-M7
    __global__ void strassen_combine(
        const __hip_bfloat16* M1,
        const __hip_bfloat16* M2,
        const __hip_bfloat16* M3,
        const __hip_bfloat16* M4,
        const __hip_bfloat16* M5,
        const __hip_bfloat16* M6,
        const __hip_bfloat16* M7,
        __hip_bfloat16* C,
        int n
    ) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        int quadrant_size = n * n / 4;
        
        if (idx < quadrant_size * 4) {
            int q = idx / quadrant_size;  // Which quadrant: 0=C11, 1=C12, 2=C21, 3=C22
            int i = idx % quadrant_size;  // Index within quadrant
            
            float m1 = __bfloat162float(M1[i]);
            float m2 = __bfloat162float(M2[i]);
            float m3 = __bfloat162float(M3[i]);
            float m4 = __bfloat162float(M4[i]);
            float m5 = __bfloat162float(M5[i]);
            float m6 = __bfloat162float(M6[i]);
            float m7 = __bfloat162float(M7[i]);
            
            float result;
            switch(q) {
                case 0: // C11 = M1 + M4 - M5 + M7
                    result = m1 + m4 - m5 + m7;
                    break;
                case 1: // C12 = M3 + M5
                    result = m3 + m5;
                    break;
                case 2: // C21 = M2 + M4
                    result = m2 + m4;
                    break;
                case 3: // C22 = M1 - M2 + M3 + M6
                    result = m1 - m2 + m3 + m6;
                    break;
                default:
                    result = 0.0f;
            }
            
            C[idx] = (__hip_bfloat16)result;
        }
    }
    
    // Helper: add/sub with result placement
    __global__ void strassen_add_sub(
        const __hip_bfloat16* A,
        const __hip_bfloat16* B,
        __hip_bfloat16* C,
        int n, int op  // 0=add, 1=sub
    ) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        int total = n * n;
        if (idx < total) {
            float a = __bfloat162float(A[idx]);
            float b = __bfloat162float(B[idx]);
            C[idx] = (__hip_bfloat16)(op == 0 ? a + b : a - b);
        }
    }
    
    void launch_add(
        torch::Tensor A, torch::Tensor B, torch::Tensor C, int n
    ) {
        int blocks = (n * n + BLOCK_SIZE - 1) / BLOCK_SIZE;
        mat_add<<<blocks, BLOCK_SIZE>>>(
            reinterpret_cast<const __hip_bfloat16*>(A.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            n
        );
    }
    
    void launch_sub(
        torch::Tensor A, torch::Tensor B, torch::Tensor C, int n
    ) {
        int blocks = (n * n + BLOCK_SIZE - 1) / BLOCK_SIZE;
        mat_sub<<<blocks, BLOCK_SIZE>>>(
            reinterpret_cast<const __hip_bfloat16*>(A.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            n
        );
    }
    
    void launch_mul_base(
        torch::Tensor A, torch::Tensor B, torch::Tensor C, int n
    ) {
        dim3 block(16, 16);
        dim3 grid((n + 15) / 16, (n + 15) / 16);
        mat_mul_base<<<grid, block>>>(
            reinterpret_cast<const __hip_bfloat16*>(A.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            n
        );
    }
    
    void launch_combine(
        torch::Tensor M1, torch::Tensor M2, torch::Tensor M3,
        torch::Tensor M4, torch::Tensor M5, torch::Tensor M6,
        torch::Tensor M7, torch::Tensor C, int n
    ) {
        int blocks = (n * n + BLOCK_SIZE - 1) / BLOCK_SIZE;
        strassen_combine<<<blocks, BLOCK_SIZE>>>(
            reinterpret_cast<const __hip_bfloat16*>(M1.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(M2.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(M3.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(M4.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(M5.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(M6.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(M7.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            n
        );
    }
    
    void launch_add_sub(
        torch::Tensor A, torch::Tensor B, torch::Tensor C,
        int n, int op
    ) {
        int blocks = (n * n + BLOCK_SIZE - 1) / BLOCK_SIZE;
        strassen_add_sub<<<blocks, BLOCK_SIZE>>>(
            reinterpret_cast<const __hip_bfloat16*>(A.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            n, op
        );
    }
    """

    CPP_SOURCE = """
    void launch_add(torch::Tensor A, torch::Tensor B, torch::Tensor C, int n);
    void launch_sub(torch::Tensor A, torch::Tensor B, torch::Tensor C, int n);
    void launch_mul_base(torch::Tensor A, torch::Tensor B, torch::Tensor C, int n);
    void launch_combine(torch::Tensor M1, torch::Tensor M2, torch::Tensor M3,
                        torch::Tensor M4, torch::Tensor M5, torch::Tensor M6,
                        torch::Tensor M7, torch::Tensor C, int n);
    void launch_add_sub(torch::Tensor A, torch::Tensor B, torch::Tensor C,
                        int n, int op);
    """

    try:
        _kernel_mod = load_inline(
            name="strassen_gemm",
            cpp_sources=[CPP_SOURCE],
            cuda_sources=[HIP_SOURCE],
            functions=[
                "launch_add",
                "launch_sub",
                "launch_mul_base",
                "launch_combine",
                "launch_add_sub",
            ],
            verbose=False,
            extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
        )
        _kernel_ok = True
    except Exception as e:
        print(f"[Strassen] Kernel build failed: {e}")
        _kernel_mod = None
        _kernel_ok = False

    return _kernel_mod, _kernel_ok


def _pad_matrix(mat: torch.Tensor, align: int) -> tuple[torch.Tensor, int, int]:
    """
    Pad matrix to align dimensions.

    Returns:
        padded: Padded matrix
        orig_M: Original M dimension
        orig_N: Original N dimension
    """
    M, N = mat.shape
    pad_M = (align - M % align) % align
    pad_N = (align - N % align) % align

    if pad_M > 0 or pad_N > 0:
        padded = torch.nn.functional.pad(mat, (0, pad_N, 0, pad_M))
        return padded, M, N
    return mat, M, N


def _extract_quadrant(mat: torch.Tensor, n: int, quadrant: int) -> torch.Tensor:
    """
    Extract a quadrant from a matrix.

    quadrants: 0=top-left, 1=top-right, 2=bottom-left, 3=bottom-right
    """
    half_n = n // 2
    if quadrant == 0:
        return mat[:half_n, :half_n].contiguous()
    elif quadrant == 1:
        return mat[:half_n, half_n:].contiguous()
    elif quadrant == 2:
        return mat[half_n:, :half_n].contiguous()
    else:  # quadrant == 3
        return mat[half_n:, half_n:].contiguous()


def _strassen_multiply_recursive(
    mod, A: torch.Tensor, B: torch.Tensor, n: int, base_size: int = STRASSEN_BASE_SIZE
) -> torch.Tensor:
    """
    Recursive Strassen matrix multiplication.

    Args:
        mod: Kernel module
        A: [n, n] matrix
        B: [n, n] matrix
        n: Dimension (must be power of 2 or multiple of base_size)
        base_size: Recursion base case size

    Returns:
        C: [n, n] result matrix
    """
    # Base case: use standard multiplication
    if n <= base_size:
        C = torch.empty((n, n), dtype=A.dtype, device=A.device)
        mod.launch_mul_base(A, B, C, n)
        return C

    # Recursive case: Strassen decomposition
    half_n = n // 2

    # Extract quadrants
    A11 = _extract_quadrant(A, n, 0)
    A12 = _extract_quadrant(A, n, 1)
    A21 = _extract_quadrant(A, n, 2)
    A22 = _extract_quadrant(A, n, 3)

    B11 = _extract_quadrant(B, n, 0)
    B12 = _extract_quadrant(B, n, 1)
    B21 = _extract_quadrant(B, n, 2)
    B22 = _extract_quadrant(B, n, 3)

    # Temporary storage for intermediate results
    T1 = torch.empty((half_n, half_n), dtype=A.dtype, device=A.device)
    T2 = torch.empty((half_n, half_n), dtype=A.dtype, device=A.device)

    # Compute M1-M7
    # M1 = (A11 + A22) * (B11 + B22)
    mod.launch_add(A11, A22, T1, half_n)
    mod.launch_add(B11, B22, T2, half_n)
    M1 = _strassen_multiply_recursive(mod, T1, T2, half_n, base_size)

    # M2 = (A21 + A22) * B11
    mod.launch_add(A21, A22, T1, half_n)
    M2 = _strassen_multiply_recursive(mod, T1, B11, half_n, base_size)

    # M3 = A11 * (B12 - B22)
    mod.launch_sub(B12, B22, T2, half_n)
    M3 = _strassen_multiply_recursive(mod, A11, T2, half_n, base_size)

    # M4 = A22 * (B21 - B11)
    mod.launch_sub(B21, B11, T2, half_n)
    M4 = _strassen_multiply_recursive(mod, A22, T2, half_n, base_size)

    # M5 = (A11 + A12) * B22
    mod.launch_add(A11, A12, T1, half_n)
    M5 = _strassen_multiply_recursive(mod, T1, B22, half_n, base_size)

    # M6 = (A21 - A11) * (B11 + B12)
    mod.launch_sub(A21, A11, T1, half_n)
    mod.launch_add(B11, B12, T2, half_n)
    M6 = _strassen_multiply_recursive(mod, T1, T2, half_n, base_size)

    # M7 = (A12 - A22) * (B21 + B22)
    mod.launch_sub(A12, A22, T1, half_n)
    mod.launch_add(B21, B22, T2, half_n)
    M7 = _strassen_multiply_recursive(mod, T1, T2, half_n, base_size)

    # Combine results using kernel
    C = torch.empty((n, n), dtype=A.dtype, device=A.device)
    mod.launch_combine(M1, M2, M3, M4, M5, M6, M7, C, n)

    return C


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
    Strassen fast matrix multiplication kernel.

    Implements Strassen's algorithm for O(n^2.81) complexity matrix multiplication.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Strassen requires square matrices for optimal performance
    # For non-square, use standard GEMM
    if M != N or M != K:
        try:
            return _aiter_gemm(data)
        except Exception as e:
            print(f"[Strassen] Aiter failed: {e}")
            return torch.matmul(A, B.t())

    # Check if size is suitable for Strassen
    if M < STRASSEN_MIN_SIZE:
        # Too small: overhead not worth it
        try:
            return _aiter_gemm(data)
        except Exception as e:
            print(f"[Strassen] Aiter failed: {e}")
            return torch.matmul(A, B.t())

    # Pad to power of 2 or alignment
    A_pad, orig_M, orig_K = _pad_matrix(A, STRASSEN_PAD_ALIGN)
    B_pad, orig_N_B, orig_K_B = _pad_matrix(B, STRASSEN_PAD_ALIGN)

    # Ensure square padded matrices
    max_dim = max(A_pad.shape[0], A_pad.shape[1], B_pad.shape[0], B_pad.shape[1])
    # Round up to next power of 2 or multiple of alignment
    pad_n = ((max_dim + STRASSEN_PAD_ALIGN - 1) // STRASSEN_PAD_ALIGN) * STRASSEN_PAD_ALIGN

    if A_pad.shape[0] < pad_n or A_pad.shape[1] < pad_n:
        A_pad = torch.nn.functional.pad(
            A_pad, (0, pad_n - A_pad.shape[1], 0, pad_n - A_pad.shape[0])
        )
    if B_pad.shape[0] < pad_n or B_pad.shape[1] < pad_n:
        B_pad = torch.nn.functional.pad(
            B_pad, (0, pad_n - B_pad.shape[1], 0, pad_n - B_pad.shape[0])
        )

    # Get kernel module
    mod, ok = _get_strassen_kernel()
    if not ok or mod is None:
        print("[Strassen] Kernel not available, using fallback")
        try:
            return _aiter_gemm(data)
        except Exception as e:
            return torch.matmul(A, B.t())

    try:
        # Convert to bfloat16 for kernel
        A_bf16 = A_pad.to(torch.bfloat16)
        B_T = B_pad.t().contiguous()
        B_bf16 = B_T.to(torch.bfloat16)

        # Perform Strassen multiplication
        C_full = _strassen_multiply_recursive(mod, A_bf16, B_bf16, pad_n, STRASSEN_BASE_SIZE)

        # Extract relevant portion and convert back
        C = C_full[:M, :N].to(A.dtype)

        return C

    except Exception as e:
        print(f"[Strassen] Execution failed: {e}, using fallback")
        try:
            return _aiter_gemm(data)
        except Exception as e2:
            print(f"[Strassen] Fallback failed: {e2}")
            return torch.matmul(A, B.t())
