#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Probe ranked shapes — print M, N, K for every call."""

import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

_call_count = 0


def custom_kernel(data: input_t) -> output_t:
    global _call_count
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    _call_count += 1
    print(f"[SHAPE] call={_call_count} M={M} N={N} K={K} MxNxK={M * N * K}")

    # Use aiter baseline (our ranked best)
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )
