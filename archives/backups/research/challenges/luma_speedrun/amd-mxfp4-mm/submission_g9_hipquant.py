#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G9: Fastest possible aiter path — HIP quant + pre-resolved refs.

Two micro-optimizations stacked:
1. per_1x32_f4_quant_hip (HIP-native) instead of dynamic_mxfp4_quant (Triton)
   — HIP quant may skip Triton JIT overhead and use native HIP stream
2. All function references pre-resolved at module load (skip attribute lookup)

For ranked shapes: M=4-256, K=512-7168. The quant takes ~2-5µs per call.
If HIP quant saves even 0.5-1µs, the geomean improves ~5-8%.
"""

import aiter
from aiter import dtypes
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Pre-resolve ALL function references at module load
_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16
_shuffle = e8m0_shuffle

# Try HIP quant first, fall back to Triton
try:
    _quant = aiter.per_1x32_f4_quant_hip
    _USE_HIP_QUANT = True
except AttributeError:
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    _quant = dynamic_mxfp4_quant
    _USE_HIP_QUANT = False


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    Aq, Asc = _quant(A.contiguous())
    Ash = _shuffle(Asc).view(_fp8_e8m0)
    return _gemm(Aq.view(_fp4x2), B_shuffle, Ash, B_scale_sh, dtype=_bf16, bpreshuffle=True)
