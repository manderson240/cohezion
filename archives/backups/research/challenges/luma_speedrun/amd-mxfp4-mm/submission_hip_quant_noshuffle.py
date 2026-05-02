#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: HIP quant (no shuffle) + separate e8m0_shuffle + gemm_a4w4.

per_1x32_f4_quant_hip(shuffle=True) produces wrong shuffle format for gemm_a4w4.
This variant uses shuffle=False then applies e8m0_shuffle separately.
The HIP quant kernel may still be faster than the Triton quant kernel.
"""

import aiter
from aiter import dtypes
from task import input_t, output_t


# Try HIP quant path WITHOUT shuffle (shuffle=True is broken)
_hip_quant = None
try:
    from aiter.ops.quant import per_1x32_f4_quant_hip

    _hip_quant = per_1x32_f4_quant_hip
except ImportError:
    pass

# Always need these
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle


_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Quantize A: HIP quant (no shuffle) + separate e8m0_shuffle
    if _hip_quant is not None:
        try:
            Aq, Asc = _hip_quant(A.contiguous(), shuffle=False)
            Ash_view = e8m0_shuffle(Asc).view(_e8m0)
        except Exception:
            Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
            Ash_view = e8m0_shuffle(Asc).view(_e8m0)
    else:
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash_view = e8m0_shuffle(Asc).view(_e8m0)

    return _gemm(
        Aq.view(_fp4x2),
        B_shuffle,
        Ash_view,
        B_scale_sh,
        dtype=_bf16,
        bpreshuffle=True,
    )
