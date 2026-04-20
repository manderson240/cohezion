"""MXFP4 GEMM — optimized aiter with minimal Python overhead.

Key insight: dynamic_mxfp4_quant + e8m0_shuffle + view are 3 separate
Python dispatch calls. Each has ~5-10us overhead. Minimize by:
1. Avoid unnecessary .view() calls
2. Use torch.no_grad() to skip autograd overhead
3. Ensure A is already contiguous (skip check)
"""

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Minimize Python dispatch: chain operations tightly
    A_q, A_scale = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)

    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
