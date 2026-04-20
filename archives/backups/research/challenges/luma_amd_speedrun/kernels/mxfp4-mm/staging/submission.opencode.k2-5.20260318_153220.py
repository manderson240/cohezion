#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""
GEMM Submission: Optimized MXFP4 GEMM using aiter gemm_a4w4.
"""

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    MXFP4 GEMM: A (bf16) x B (MXFP4) -> C (bf16)
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    # Quantize A to MXFP4 with shuffled scales
    A_q_raw, A_scale_raw = dynamic_mxfp4_quant(A)
    A_scale_shuffled = e8m0_shuffle(A_scale_raw).view(dtypes.fp8_e8m0)
    A_q = A_q_raw.view(dtypes.fp4x2)

    # Call aiter GEMM kernel with bpreshuffle=True
    C = aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_shuffled,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )

    return C
