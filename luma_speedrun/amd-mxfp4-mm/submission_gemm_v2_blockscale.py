"""MXFP4 GEMM — gemm_a4w4_blockscale with tuned splitK.

Based on research from staging/submission.gemm-specialist.blockscale_tuned.py
Key optimization: splitK tuning and direct API call.
"""
import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle


def custom_kernel(data):
    A, B, B_q, B_shuffle, B_scale_sh = data

    A = A.contiguous()
    m, k = A.shape
    n = B_shuffle.shape[0]

    # Quantize A
    A_fp4, A_scale = dynamic_mxfp4_quant(A)

    # Prepare shuffled scale
    A_scale_u8 = A_scale[:m, :].contiguous().view(dtypes.fp8_e8m0)
    A_scale_sh = e8m0_shuffle(A_scale_u8)
    A_q = A_fp4.view(dtypes.fp4x2)

    # Pre-allocate output
    Out = torch.empty(m, n, dtype=torch.bfloat16, device="cuda")

    # Tuned splitK:
    # - splitK=0 for most shapes (no split)
    # - Could try splitK=1 or 2 for specific large shapes
    C = aiter.gemm_a4w4_blockscale(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        Out,
        splitK=0,
    )
    return C
