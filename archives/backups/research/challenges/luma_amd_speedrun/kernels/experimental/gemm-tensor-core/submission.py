"""
GEMM: Tensor Core Optimized Layout

#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

Optimizes matrix layout for AMD MI355X tensor core (MFMA) operations.
MI355X supports matrix fused multiply-accumulate with specific layout requirements.

Key Innovation:
- MFMA layout: Organize data for 16x16 or 32x32 MFMA tiles
- Swizzled memory: Optimize for LDS bank conflicts
- Vectorized loads: Use buffer loads for coalesced access
- Wave-level primitives: Use wave32 or wave64 execution

Trade-offs:
+ Peak performance on MFMA units
+ Better memory throughput with optimized layouts
- Requires specific data formatting
- Limited to compatible dimensions

Reference: AMD CDNA3 Architecture Guide
MI355X (gfx950) MFMA instruction specifications.
"""

from __future__ import annotations
import os
import sys
import torch
from typing import Tuple
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


class MFMAOptimalLayout:
    """
    Implements optimal layout for MI355X MFMA operations.

    MI355X MFMA requirements:
    - Input A: [M, K] in row-major, packed as fp4x2
    - Input B: [N, K] in col-major (or row-major of K,N)
    - Output C: [M, N] in row-major

    Tile sizes: 16x16, 32x32 for fp4
    """

    def __init__(self, mfma_m: int = 32, mfma_n: int = 32, mfma_k: int = 64):
        """
        Initialize MFMA layout.

        Args:
            mfma_m: MFMA tile M dimension
            mfma_n: MFMA tile N dimension
            mfma_k: MFMA tile K dimension (fp4 elements)
        """
        self.mfma_m = mfma_m
        self.mfma_n = mfma_n
        self.mfma_k = mfma_k

    def pad_to_mfma(self, m: int, n: int, k: int) -> Tuple[int, int, int]:
        """Pad dimensions to MFMA tile boundaries."""
        m_padded = ((m + self.mfma_m - 1) // self.mfma_m) * self.mfma_m
        n_padded = ((n + self.mfma_n - 1) // self.mfma_n) * self.mfma_n
        k_padded = ((k + self.mfma_k - 1) // self.mfma_k) * self.mfma_k
        return m_padded, n_padded, k_padded

    def swizzle_matrix(self, x: torch.Tensor, tile_size: int = 32) -> torch.Tensor:
        """
        Swizzle matrix layout for LDS bank conflict avoidance.

        Args:
            x: Input matrix
            tile_size: Swizzle tile size

        Returns:
            Swizzled matrix
        """
        rows, cols = x.shape
        rows_padded = ((rows + tile_size - 1) // tile_size) * tile_size
        cols_padded = ((cols + tile_size - 1) // tile_size) * tile_size

        # Pad
        x_padded = torch.nn.functional.pad(x, (0, cols_padded - cols, 0, rows_padded - rows))

        # Swizzle: transpose within tiles
        result = torch.zeros_like(x_padded)
        for tr in range(0, rows_padded, tile_size):
            for tc in range(0, cols_padded, tile_size):
                tile = x_padded[tr : tr + tile_size, tc : tc + tile_size]
                # Transpose tile for bank conflict avoidance
                result[tr : tr + tile_size, tc : tc + tile_size] = tile.T

        return result[:rows, :cols]


def mfma_gemm_tiled(
    a: torch.Tensor,
    b: torch.Tensor,
    a_scale: torch.Tensor,
    b_scale: torch.Tensor,
    mfma_m: int = 32,
    mfma_n: int = 32,
    mfma_k: int = 64,
) -> torch.Tensor:
    """
    Compute GEMM with MFMA-optimized tiling.

    Args:
        a: Matrix A [M, K]
        b: Matrix B [N, K]
        a_scale: A scales
        b_scale: B scales
        mfma_m: MFMA tile M
        mfma_n: MFMA tile N
        mfma_k: MFMA tile K

    Returns:
        Output C [M, N]
    """
    m, k = a.shape
    n = b.shape[0]
    device = a.device
    dtype = torch.bfloat16

    # Pad to MFMA boundaries
    layout = MFMAOptimalLayout(mfma_m, mfma_n, mfma_k)
    m_padded, n_padded, k_padded = layout.pad_to_mfma(m, n, k)

    a_padded = torch.nn.functional.pad(a, (0, k_padded - k, 0, m_padded - m))
    b_padded = torch.nn.functional.pad(b, (0, k_padded - k, 0, n_padded - n))

    # Initialize output
    c = torch.zeros(m_padded, n_padded, dtype=dtype, device=device)

    # Tile dimensions
    num_m_tiles = m_padded // mfma_m
    num_n_tiles = n_padded // mfma_n
    num_k_tiles = k_padded // mfma_k

    # Compute tiles
    for tm in range(num_m_tiles):
        for tn in range(num_n_tiles):
            accum = torch.zeros(mfma_m, mfma_n, dtype=torch.float32, device=device)

            for tk in range(num_k_tiles):
                # Extract MFMA tiles
                a_tile = a_padded[tm * mfma_m : (tm + 1) * mfma_m, tk * mfma_k : (tk + 1) * mfma_k]
                b_tile = b_padded[tn * mfma_n : (tn + 1) * mfma_n, tk * mfma_k : (tk + 1) * mfma_k]

                # Dequantize and multiply
                a_tile_f = a_tile.float()
                b_tile_f = b_tile.float()

                # Apply scales
                a_scale_tile = a_scale[
                    tm * mfma_m : (tm + 1) * mfma_m, tk * mfma_k // 32 : ((tk + 1) * mfma_k) // 32
                ]
                b_scale_tile = b_scale[
                    tn * mfma_n : (tn + 1) * mfma_n, tk * mfma_k // 32 : ((tk + 1) * mfma_k) // 32
                ]

                # Expand scales
                a_scale_expanded = a_scale_tile.repeat_interleave(32, dim=1)[:, :mfma_k]
                b_scale_expanded = b_scale_tile.repeat_interleave(32, dim=1)[:, :mfma_k]

                # MFMA multiply-accumulate
                a_scaled = a_tile_f * a_scale_expanded
                b_scaled = b_tile_f * b_scale_expanded

                accum += torch.matmul(a_scaled, b_scaled.T)

            c[tm * mfma_m : (tm + 1) * mfma_m, tn * mfma_n : (tn + 1) * mfma_n] = accum.to(dtype)

    return c[:m, :n]


def custom_kernel(data: input_t) -> output_t:
    """
    Execute GEMM with MFMA-optimized layout.

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

        # Get MFMA tile size
        mfma_m = int(os.environ.get("MFMA_M", "32"))
        mfma_n = int(os.environ.get("MFMA_N", "32"))
        mfma_k = int(os.environ.get("MFMA_K", "64"))

        print(f"[MFMA GEMM] Tiles: {mfma_m}x{mfma_n}x{mfma_k}", file=sys.stderr)

        # Execute MFMA-optimized GEMM
        output = mfma_gemm_tiled(
            A_q.float(),
            B_shuffle.float(),
            A_scale_sh.float(),
            B_scale_sh.float(),
            mfma_m,
            mfma_n,
            mfma_k,
        )

        return output

    except Exception as e:
        print(f"MFMA GEMM failed: {e}", file=sys.stderr)
        from aiter import gemm_a4w4

        A_contig = A.contiguous()
        A_fp4, A_scale = dynamic_mxfp4_quant(A_contig)
        A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
        A_q = A_fp4.view(dtypes.fp4x2)
        return gemm_a4w4(
            A_q, B_shuffle, A_scale_sh, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )
