"""
GEMM: Strassen's Algorithm (Fast Matrix Multiplication)

#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

Implements Strassen's algorithm for fast matrix multiplication, reducing
the asymptotic complexity from O(n^3) to O(n^2.81) by using clever additions
and only 7 multiplications instead of 8 for 2x2 block decomposition.

Key Innovation:
- Block decomposition: Split matrices into quadrants
- Strassen products: 7 clever products (M1-M7) instead of 8 standard
- Recursive application: Apply recursively for large matrices
- Base case switching: Use standard GEMM for small blocks

Trade-offs:
+ Fewer multiplications (7 vs 8 per level)
- More additions (18 vs 4 per level)
- Numerical stability concerns from cancellation
- Memory overhead for intermediate products

Reference: Strassen, V. (1969). "Gaussian elimination is not optimal"
Applied to GPU: Blocked recursive implementation with size cutoff.
"""

from __future__ import annotations

import os
import sys

import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


class StrassenGEMM:
    """
    Implements Strassen's fast matrix multiplication algorithm.

    For matrices A, B, C where C = A @ B^T:
    Split into quadrants:
        A = [[A11, A12], [A21, A22]]
        B = [[B11, B12], [B21, B22]]
        C = [[C11, C12], [C21, C22]]

    Strassen products:
        M1 = (A11 + A22) @ (B11 + B22)
        M2 = (A21 + A22) @ B11
        M3 = A11 @ (B12 - B22)
        M4 = A22 @ (B21 - B11)
        M5 = (A11 + A12) @ B22
        M6 = (A21 - A11) @ (B11 + B12)
        M7 = (A12 - A22) @ (B21 + B22)

    Result quadrants:
        C11 = M1 + M4 - M5 + M7
        C12 = M3 + M5
        C21 = M2 + M4
        C22 = M1 - M2 + M3 + M6
    """

    def __init__(self, base_size: int = 64, max_depth: int = 3):
        """
        Initialize Strassen GEMM.

        Args:
            base_size: Size below which to use standard GEMM
            max_depth: Maximum recursion depth
        """
        self.base_size = base_size
        self.max_depth = max_depth

    def pad_to_power_of_2(self, tensor: torch.Tensor) -> torch.Tensor:
        """Pad tensor dimensions to next power of 2."""
        shape = list(tensor.shape)
        new_shape = []
        for dim in shape:
            if dim <= 1:
                new_shape.append(dim)
            else:
                new_shape.append(1 << (dim - 1).bit_length())

        if new_shape == shape:
            return tensor

        pad_dims = []
        for i, (old, new) in enumerate(zip(shape, new_shape)):
            if old < new:
                pad_dims.extend([0, new - old])
            else:
                pad_dims.extend([0, 0])

        return torch.nn.functional.pad(tensor, pad_dims[::-1])

    def strassen_multiply(self, a: torch.Tensor, b: torch.Tensor, depth: int = 0) -> torch.Tensor:
        """
        Recursively multiply matrices using Strassen's algorithm.

        Args:
            a: Matrix A [M, K]
            b: Matrix B [N, K] (note: we use B^T in actual matmul)
            depth: Current recursion depth

        Returns:
            Result C [M, N]
        """
        m, k = a.shape
        n = b.shape[0]

        # Base case: use standard multiplication
        if (
            m <= self.base_size
            or n <= self.base_size
            or k <= self.base_size
            or depth >= self.max_depth
        ):
            return torch.matmul(a, b.T)

        # Ensure dimensions are even for splitting
        mid_m = m // 2
        mid_n = n // 2
        mid_k = k // 2

        # Split matrices into quadrants
        a11 = a[:mid_m, :mid_k]
        a12 = a[:mid_m, mid_k:]
        a21 = a[mid_m:, :mid_k]
        a22 = a[mid_m:, mid_k:]

        b11 = b[:mid_n, :mid_k]
        b12 = b[:mid_n, mid_k:]
        b21 = b[mid_n:, :mid_k]
        b22 = b[mid_n:, mid_k:]

        # Compute Strassen products recursively
        m1 = self.strassen_multiply(a11 + a22, b11 + b22, depth + 1)
        m2 = self.strassen_multiply(a21 + a22, b11, depth + 1)
        m3 = self.strassen_multiply(a11, b12 - b22, depth + 1)
        m4 = self.strassen_multiply(a22, b21 - b11, depth + 1)
        m5 = self.strassen_multiply(a11 + a12, b22, depth + 1)
        m6 = self.strassen_multiply(a21 - a11, b11 + b12, depth + 1)
        m7 = self.strassen_multiply(a12 - a22, b21 + b22, depth + 1)

        # Compute result quadrants
        c11 = m1 + m4 - m5 + m7
        c12 = m3 + m5
        c21 = m2 + m4
        c22 = m1 - m2 + m3 + m6

        # Combine quadrants
        c_top = torch.cat([c11, c12], dim=1)
        c_bottom = torch.cat([c21, c22], dim=1)
        c = torch.cat([c_top, c_bottom], dim=0)

        return c[:m, :n]


def custom_kernel(data: input_t) -> output_t:
    """
    Execute GEMM with Strassen's algorithm.

    Args:
        data: Tuple of (A_bf16, B_bf16, B_q_fp4x2, B_shuffle, B_scale_sh_e8m0)

    Returns:
        Output matrix C [M, N]
    """
    A, B, _B_q, B_shuffle, B_scale_sh = data

    m = A.shape[0]
    n = B_shuffle.shape[0]
    k = A.shape[1]

    try:
        # Quantize A
        A_contig = A.contiguous()
        A_fp4, A_scale = dynamic_mxfp4_quant(A_contig)
        A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
        A_q = A_fp4.view(dtypes.fp4x2)

        # Get Strassen parameters
        base_size = int(os.environ.get("STRASSEN_BASE", "64"))
        max_depth = int(os.environ.get("STRASSEN_DEPTH", "3"))

        # Only use Strassen for large enough matrices
        if m >= base_size and n >= base_size and k >= base_size:
            strassen = StrassenGEMM(base_size, max_depth)
            output = strassen.strassen_multiply(A_q.float(), B_shuffle.float())
            return output.to(torch.bfloat16)
        else:
            # Small matrix - use standard GEMM
            from aiter import gemm_a4w4

            return gemm_a4w4(
                A_q, B_shuffle, A_scale_sh, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
            )

    except Exception as e:
        print(f"Strassen failed: {e}", file=sys.stderr)
        from aiter import gemm_a4w4

        A_contig = A.contiguous()
        A_fp4, A_scale = dynamic_mxfp4_quant(A_contig)
        A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
        A_q = A_fp4.view(dtypes.fp4x2)
        return gemm_a4w4(
            A_q, B_shuffle, A_scale_sh, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )
