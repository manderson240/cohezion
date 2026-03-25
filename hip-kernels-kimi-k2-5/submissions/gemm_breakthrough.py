"""GEMM Breakthrough: Maximum optimization for Top 10.

Target: 9.671µs (leader) vs current ~20.8µs
Strategy: Shape-adaptive kernel selection with aggressive split-K
"""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """Optimized GEMM with shape-aware kernel selection for MI355X."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M, K = A.shape
    N = B.shape[0]

    # Quantize A with MXFP4
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    A_q = x_fp4.view(dtypes.fp4x2)

    # Aggressive shape-adaptive kernel selection based on AITER research
    if M <= 4:
        # Tiny M: maximum parallelism
        kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
        log2_ks = 4  # 16-way split
    elif M <= 8 or M <= 16:
        kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
        log2_ks = 3  # 8-way split
    elif M <= 32:
        # Medium M: moderate parallelism
        if N <= 256:
            kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
        elif N <= 512:
            kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x256E"
        else:
            kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x512E"
        log2_ks = 2  # 4-way split
    elif M <= 64:
        # Large M: minimal split
        kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_128x128E"
        log2_ks = 1  # 2-way split
    elif M <= 128:
        kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"
        log2_ks = 0  # No split
    else:
        # Very large M: large tiles, no split
        kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_256x128E"
        log2_ks = 0  # No split

    out = torch.empty(M, N, dtype=torch.bfloat16, device="cuda")

    return aiter.gemm_a4w4_asm(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        out,
        kernel_name,
        bpreshuffle=True,
        log2_k_split=log2_ks,
    )
