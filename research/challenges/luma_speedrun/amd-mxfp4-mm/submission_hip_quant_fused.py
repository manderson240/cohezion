#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Use per_1x32_f4_quant_hip(shuffle=True) for single-call quant+shuffle.

Discovery from leader analysis: the standard path uses TWO kernel launches:
1. dynamic_mxfp4_quant(A)  — Triton kernel
2. e8m0_shuffle(A_scale)   — Python tensor op

per_1x32_f4_quant_hip(A, shuffle=True) does BOTH in a single HIP C++ kernel.
This saves one kernel launch (~1-2µs on ranked runner).

Combined with gemm_a4w4 (NOT _asm) which is ranked-optimal at 13.4µs.
"""

import torch
import aiter
from aiter import dtypes
from task import input_t, output_t

# Try the HIP quant path
try:
    from aiter.ops.quant import per_1x32_f4_quant_hip

    _hip_quant = per_1x32_f4_quant_hip
    _use_hip = True
except ImportError:
    _use_hip = False

# Pre-resolve for fast dispatch
_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    if _use_hip:
        # Single HIP kernel: quant + shuffle in one pass
        Aq, Ash = _hip_quant(A.contiguous(), shuffle=True)
        return _gemm(
            Aq.view(_fp4x2),
            B_shuffle,
            Ash.view(_fp8_e8m0),
            B_scale_sh,
            dtype=_bf16,
            bpreshuffle=True,
        )
    else:
        # Fallback: two-call path
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from aiter.utility.fp4_utils import e8m0_shuffle

        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(_fp8_e8m0)
        return _gemm(
            Aq.view(_fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=_bf16,
            bpreshuffle=True,
        )
