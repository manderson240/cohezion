#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""
GEMM Final Push: Standard-Optimized Strategy.
- Uses #975-patched Triton Quantizer for bit-accuracy.
- Uses standard aiter.gemm_a4w4 (no manual buffer management).
- Optimized for Ranked Shapes via high-level aiter robustness.
"""

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant  # #975-patched
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


_gemm_fn = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def _quant_mxfp4(x):
    # Pure aiter flow, no manual management
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(x.contiguous())
    bs_e8m0 = e8m0_shuffle(bs_e8m0)
    return x_fp4.view(_fp4x2), bs_e8m0.view(_e8m0)


def custom_kernel(data: input_t) -> output_t:
    # Tuple: (A, B, B_q, B_shuffle, B_scale_sh)
    A, B, B_q, B_shuffle, B_scale_sh = data

    # 1. Quantize A using official patched kernel
    Aq, Ash = _quant_mxfp4(A)

    # 2. Standard aiter GEMM
    # No manual 'out' or pre-allocated buffers to avoid interfering with JIT.
    return _gemm_fn(Aq, B_shuffle, Ash, B_scale_sh, dtype=_bf16, bpreshuffle=True)
