"""GEMM v17 - Conservative baseline for comparison."""

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """Conservative GEMM with minimal split-K."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M = A.shape[0]

    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    A_q = x_fp4.view(dtypes.fp4x2)

    # Conservative: minimal split-K
    if M <= 8:
        log2_ks = 1  # 2-way split
    else:
        log2_ks = 0  # No split

    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
