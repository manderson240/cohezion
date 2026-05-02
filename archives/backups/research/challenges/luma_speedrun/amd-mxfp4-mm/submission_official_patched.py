#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Official GEMM Submission: uses #975-patched dynamic_mxfp4_quant.

Aligned with official spec:
- Uses aiter.ops.triton.quant.dynamic_mxfp4_quant (patched kernel)
- GEMM: aiter.gemm_a4w4
- Matches official 'Leader Pattern'
"""

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant  # #975-patched kernel
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Pre-resolve for minimal overhead
_gemm_fn = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def _quant_mxfp4(x, shuffle=True):
    """Exactly matches provided reference logic."""
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(x)
    if shuffle:
        bs_e8m0 = e8m0_shuffle(bs_e8m0)
    return x_fp4.view(_fp4x2), bs_e8m0.view(_e8m0)


def custom_kernel(data: input_t) -> output_t:
    # Tuple: (A, B, B_q, B_shuffle, B_scale_sh)
    A, B, B_q, B_shuffle, B_scale_sh = data

    # 1. Quantize A using patched Triton kernel
    Aq, Ash = _quant_mxfp4(A.contiguous(), shuffle=True)

    # 2. GEMM: use gemm_a4w4
    return _gemm_fn(Aq, B_shuffle, Ash, B_scale_sh, dtype=_bf16, bpreshuffle=True)
