#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G8: Minimal Python overhead aiter path.

Reduce the ~2µs Python overhead between aiter's 11.5µs ref and our 13.4µs:
1. Pre-import everything at module level
2. Use gemm_a4w4 directly (not through wrapper)
3. Minimize tensor operations
4. Cache shuffle result for repeated B
"""

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Pre-resolve function references at module load
_gemm = aiter.gemm_a4w4
_quant = dynamic_mxfp4_quant
_shuffle = e8m0_shuffle
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    Aq, Asc = _quant(A.contiguous())
    Ash = _shuffle(Asc).view(_fp8_e8m0)
    return _gemm(Aq.view(_fp4x2), B_shuffle, Ash, B_scale_sh,
                 dtype=_bf16, bpreshuffle=True)
