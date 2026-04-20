#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Leader pattern: per_1x32_f4_quant_hip + gemm_a4w4 with splitK=0.

Based on leader analysis:
1. Leader's file is v78_splitk0.py — explicitly uses log2_k_split=0
2. per_1x32_f4_quant_hip(shuffle=True) does quant+shuffle in single HIP kernel
3. gemm_a4w4 (NOT _asm) is ranked-optimal dispatch

This combines the fastest known quant path with the optimal GEMM dispatch.
"""

import torch
import aiter
from aiter import dtypes
from task import input_t, output_t

# Try HIP quant path (single-call quant + shuffle)
_hip_quant = None
try:
    from aiter.ops.quant import per_1x32_f4_quant_hip

    _hip_quant = per_1x32_f4_quant_hip
except ImportError:
    pass

# Fallback imports
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle

# Pre-resolve
_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Quantize A: prefer HIP single-call, fallback to Triton two-call
    if _hip_quant is not None:
        try:
            Aq, Ash = _hip_quant(A.contiguous(), shuffle=True)
            Ash_view = Ash.view(_e8m0)
        except Exception:
            Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
            Ash_view = e8m0_shuffle(Asc).view(_e8m0)
    else:
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash_view = e8m0_shuffle(Asc).view(_e8m0)

    # GEMM: use gemm_a4w4 (NOT _asm) — ranked-optimal dispatch
    return _gemm(
        Aq.view(_fp4x2),
        B_shuffle,
        Ash_view,
        B_scale_sh,
        dtype=_bf16,
        bpreshuffle=True,
    )
