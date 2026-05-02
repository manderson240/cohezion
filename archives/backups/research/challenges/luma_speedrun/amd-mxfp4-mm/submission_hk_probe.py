#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Check if HipKittens is available on the runner."""

import os

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Check for HipKittens
    try:
        import hipkittens

        print(f"[HK] hipkittens available! version={getattr(hipkittens, '__version__', '?')}")
        print(f"[HK] dir: {[x for x in dir(hipkittens) if not x.startswith('_')][:20]}")
    except ImportError:
        print("[HK] hipkittens NOT available as Python module")

    # Check for HK headers in aiter
    hk_paths = [
        "/home/runner/aiter/hipkittens",
        "/home/runner/hipkittens",
        "/usr/local/include/hipkittens",
        "/opt/rocm/include/hipkittens",
    ]
    for p in hk_paths:
        if os.path.exists(p):
            print(f"[HK] Found at: {p}")
            files = os.listdir(p)[:10]
            print(f"[HK] Files: {files}")

    # Check if HK is in aiter's backend
    hk_in_aiter = [
        x for x in dir(aiter) if "hk" in x.lower() or "kitten" in x.lower() or "hipk" in x.lower()
    ]
    if hk_in_aiter:
        print(f"[HK] In aiter: {hk_in_aiter}")
    else:
        print("[HK] Not found in aiter namespace")

    # Standard GEMM
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )
