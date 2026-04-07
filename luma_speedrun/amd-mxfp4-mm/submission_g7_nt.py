#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G7: AITER_USE_NT=1 + AITER_BYPASS_TUNE_CONFIG=1 combined.

Non-temporal loads may help for streaming access patterns.
Combined with bypass to skip CSV lookup overhead.
"""

import os
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )
