"""
GEMM v18 Hybrid: Adaptive kernel selection with per-shape tile sizes.

Selects optimal ASM kernel name and log2_k_split based on M dimension:
- M <= 8:  32x128 tile, log2_ks=3  (high split-K for tiny M)
- M <= 32: 32x128 tile, log2_ks=2  (moderate split-K)
- M > 32:  192x128 tile, log2_ks=0 (large tile, no split-K)

Uses gemm_a4w4_asm directly for maximum control over kernel dispatch.
"""

from __future__ import annotations

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


KERNEL_32X128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
KERNEL_192X128 = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]

    # Quantize A to MXFP4 with dynamic per-1x32 block scaling
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)

    # Adaptive kernel selection based on M dimension
    if m <= 8:
        kernel_name = KERNEL_32X128
        log2_ks = 3
    elif m <= 32:
        kernel_name = KERNEL_32X128
        log2_ks = 2
    else:
        kernel_name = KERNEL_192X128
        log2_ks = 0

    # Pre-allocate output
    out = torch.empty((m, n), dtype=dtypes.bf16, device=A.device)

    # Direct ASM dispatch
    aiter.gemm_a4w4_asm(
        A_q.view(m, k // 2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        out,
        kernelName=kernel_name,
        bias=None,
        alpha=1.0,
        beta=0.0,
        bpreshuffle=True,
        log2_k_split=log2_ks,
    )
    return out
