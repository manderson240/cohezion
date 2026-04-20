#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G1: Per-shape timing probe — identical to ranked-best aiter baseline
but prints per-call timing to identify which shapes dominate geomean."""

import time
import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

_call = 0


def custom_kernel(data: input_t) -> output_t:
    global _call
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    _call += 1

    torch.cuda.synchronize()
    t0 = time.perf_counter()

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    out = aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )

    torch.cuda.synchronize()
    t1 = time.perf_counter()
    us = (t1 - t0) * 1e6
    print(f"[TIME] call={_call} M={M} N={N} K={K} time={us:.1f}us")
    return out
