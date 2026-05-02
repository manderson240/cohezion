"""Test: Does the runner scan the SOURCE for 'load_inline' text?

This file contains the STRING "load_inline" in comments but does NOT
import or call it. If this ALSO fails, the runner does source scanning.
"""

# NOTE: torch.utils.cpp_extension.load_inline is NOT imported here

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """Pure aiter GEMM — no load_inline anywhere."""
    A, B, B_q, B_shuffle, B_scale_sh = data

    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
