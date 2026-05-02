#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Try hipb_mm, rocb_mm, compute_gemm_SplitK, deepgemm signatures."""

import inspect

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Probe signatures
    for name in [
        "hipb_mm",
        "rocb_mm",
        "compute_gemm_SplitK",
        "deepgemm",
        "gemm_a4w4_blockscale",
        "gemm_a16w16_asm",
    ]:
        try:
            fn = getattr(aiter, name)
            sig = str(inspect.signature(fn))
            print(f"[PROBE] {name}: {sig[:300]}")
        except Exception as e:
            print(f"[PROBE] {name}: error={e}")

    # Try hipb_mm with bf16 inputs (it's a general GEMM)
    M, K = A.shape
    N = B.shape[0]
    try:
        out = aiter.hipb_mm(A, B.t(), dtype=dtypes.bf16)
        max_err = (out - A @ B.t()).abs().max().item()
        print(f"[PROBE] hipb_mm bf16: works! max_err={max_err:.6f}")
    except Exception as e:
        print(f"[PROBE] hipb_mm bf16: {e}")

    # Try rocb_mm
    try:
        out = aiter.rocb_mm(A, B.t(), dtype=dtypes.bf16)
        max_err = (out - A @ B.t()).abs().max().item()
        print(f"[PROBE] rocb_mm bf16: works! max_err={max_err:.6f}")
    except Exception as e:
        print(f"[PROBE] rocb_mm bf16: {e}")

    # Standard aiter path
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
