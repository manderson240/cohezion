#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G6: AITER_BYPASS_TUNE_CONFIG=1 — skip CSV lookup for kernel selection.

May select a faster default kernel vs the tuned one. Zero code change,
just environment variable. Uses the same aiter baseline kernel path.
"""

import os


os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
