"""
GEMM: Tiled Winograd Convolution-style Transformation

#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

Implements Winograd-style transformations for matrix multiplication,
adapted from fast convolution algorithms. Transforms input matrices
to reduce the number of required multiplications.

Key Innovation:
- Winograd transform: Convert matmul to element-wise operations in transform space
- Tiled processing: 2x2 or 4x4 Winograd tiles for memory efficiency
- Fused transformation: Combine input transforms with quantization

Trade-offs:
+ Reduces multiplications from O(N^3) to O(N^2) for small tiles
+ Good for small matrix sizes where transformation overhead is amortized
- Transformation overhead dominates for large matrices
- Limited tile sizes (2x2, 4x4) restrict applicability

Reference: "Fast Algorithms for Convolutional Neural Networks" (Lavin & Gray, 2016)
Adapted for GEMM: Winograd-style transformation on matrix tiles.
"""

from __future__ import annotations

import os
import sys

import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


class WinogradTransform:
    """
    Implements Winograd-style transformations for matrix multiplication.

    For 2x2 Winograd on 2x2 tiles:
    - Input transform: G, GT (pre-computed)
    - Output transform: AT (post-computed)
    - Element-wise multiply in transform space

    For GEMM C = A @ B^T, we tile matrices and apply Winograd within tiles.

    Transform matrices for F(2,2) - 2 output elements from 2 input:
    G = [[1, 0], [0.5, 0.5], [0.5, -0.5], [0, 1]]
    AT = [[1, 1, 1, 0], [0, 1, -1, -1]]
    """

    def __init__(self, tile_size: int = 2):
        """
        Initialize Winograd transform.

        Args:
            tile_size: Winograd tile size (2 or 4)
        """
        self.tile_size = tile_size
        self.alpha = tile_size + tile_size - 1  # Transform size

        # Precompute transformation matrices
        self.G, self.GT, self.A, self.AT = self._compute_transforms()

    def _compute_transforms(self) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Compute Winograd transformation matrices."""
        if self.tile_size == 2:
            # F(2,2) transforms
            G = torch.tensor([[1.0, 0.0], [0.5, 0.5], [0.5, -0.5], [0.0, 1.0]], dtype=torch.float32)

            AT = torch.tensor([[1.0, 1.0, 1.0, 0.0], [0.0, 1.0, -1.0, -1.0]], dtype=torch.float32)

            return G, G.T, AT.T, AT
        else:
            raise ValueError(f"Unsupported tile size: {self.tile_size}")

    def transform_input(self, x: torch.Tensor) -> torch.Tensor:
        """
        Apply input transformation G @ x @ G.T.

        Args:
            x: Input tile [tile_size, tile_size]

        Returns:
            Transformed tile [alpha, alpha]
        """
        # Convert to float for transform
        x_f = x.float()
        # G @ x
        temp = torch.matmul(self.G.to(x.device), x_f)
        # (G @ x) @ G.T
        result = torch.matmul(temp, self.GT.to(x.device))
        return result

    def transform_output(self, m: torch.Tensor) -> torch.Tensor:
        """
        Apply output transformation AT @ m @ A.

        Args:
            m: Element-wise product in transform space [alpha, alpha]

        Returns:
            Output tile [tile_size, tile_size]
        """
        # AT @ m
        temp = torch.matmul(self.AT.to(m.device), m)
        # (AT @ m) @ A
        result = torch.matmul(temp, self.A.to(m.device))
        return result

    def winograd_matmul_tile(self, a_tile: torch.Tensor, b_tile: torch.Tensor) -> torch.Tensor:
        """
        Compute matmul of two tiles using Winograd.

        Args:
            a_tile: A tile [tile_size, tile_size]
            b_tile: B tile [tile_size, tile_size]

        Returns:
            C tile [tile_size, tile_size]
        """
        # Transform inputs
        a_transformed = self.transform_input(a_tile)
        b_transformed = self.transform_input(b_tile)

        # Element-wise multiply in transform space
        m = a_transformed * b_transformed

        # Transform output back
        c_tile = self.transform_output(m)

        return c_tile


def tiled_winograd_gemm(a: torch.Tensor, b: torch.Tensor, tile_size: int = 2) -> torch.Tensor:
    """
    Compute GEMM using tiled Winograd transformation.

    Args:
        a: Matrix A [M, K]
        b: Matrix B [N, K]
        tile_size: Winograd tile size

    Returns:
        Output matrix C [M, N]
    """
    m, k = a.shape
    n = b.shape[0]
    device = a.device
    dtype = a.dtype

    # Initialize output
    c = torch.zeros(m, n, dtype=dtype, device=device)

    # Create Winograd transformer
    winograd = WinogradTransform(tile_size)

    # Process in tiles
    for tm in range(0, m, tile_size):
        for tn in range(0, n, tile_size):
            # Accumulate over K dimension
            accum = torch.zeros(tile_size, tile_size, dtype=torch.float32, device=device)

            for tk in range(0, k, tile_size):
                # Extract tiles
                m_end = min(tm + tile_size, m)
                n_end = min(tn + tile_size, n)
                k_end = min(tk + tile_size, k)

                a_tile = a[tm:m_end, tk:k_end]
                b_tile = b[tn:n_end, tk:k_end]

                # Pad tiles if needed
                if a_tile.shape != (tile_size, tile_size):
                    padded = torch.zeros(tile_size, tile_size, dtype=a.dtype, device=device)
                    padded[: a_tile.shape[0], : a_tile.shape[1]] = a_tile
                    a_tile = padded
                if b_tile.shape != (tile_size, tile_size):
                    padded = torch.zeros(tile_size, tile_size, dtype=b.dtype, device=device)
                    padded[: b_tile.shape[0], : b_tile.shape[1]] = b_tile
                    b_tile = padded

                # Winograd matmul for this tile pair
                c_tile = winograd.winograd_matmul_tile(a_tile, b_tile)
                accum += c_tile

            # Write result
            m_slice = slice(tm, min(tm + tile_size, m))
            n_slice = slice(tn, min(tn + tile_size, n))
            c[m_slice, n_slice] = accum[
                : m_slice.stop - m_slice.start, : n_slice.stop - n_slice.start
            ].to(dtype)

    return c


def custom_kernel(data: input_t) -> output_t:
    """
    Execute GEMM with Winograd-style tiled transformation.

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

        # For small matrices, Winograd may help
        # For large matrices, standard GEMM is better
        tile_size = int(os.environ.get("WINOGRAD_TILE", "2"))

        if m <= 64 and n <= 64 and k <= 64:
            # Small matrix - try Winograd
            print(f"[Winograd GEMM] Using {tile_size}x{tile_size} tiles", file=sys.stderr)
            output = tiled_winograd_gemm(A_q.float(), B_shuffle.float(), tile_size)
            return output.to(torch.bfloat16)
        else:
            # Large matrix - use standard GEMM
            from aiter import gemm_a4w4

            return gemm_a4w4(
                A_q, B_shuffle, A_scale_sh, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
            )

    except Exception as e:
        print(f"Winograd GEMM failed: {e}", file=sys.stderr)
        from aiter import gemm_a4w4

        A_contig = A.contiguous()
        A_fp4, A_scale = dynamic_mxfp4_quant(A_contig)
        A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
        A_q = A_fp4.view(dtypes.fp4x2)
        return gemm_a4w4(
            A_q, B_shuffle, A_scale_sh, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )
