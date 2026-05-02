#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Clean GEMM baseline: aiter API only, no custom kernels.

Uses the proven path: dynamic_mxfp4_quant + e8m0_shuffle + gemm_a4w4.
This is the exact path that achieved 13.425µs on the ranked leaderboard.
No load_inline, no hip_quant, no custom MFMA — pure aiter API.
"""

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(_e8m0)

    return _gemm(
        Aq.view(_fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=_bf16,
        bpreshuffle=True,
    )
