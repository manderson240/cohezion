#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM - Optimized version with minimal overhead.

Key optimizations:
1. AITER_BYPASS_TUNE_CONFIG=1 for direct dispatch
2. Avoid redundant contiguous() calls
3. Use inplace operations where possible
"""

import os


os.environ["AITER_JIT_DIR"] = "/tmp/aiter_jit_cache"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in os.environ.get("PYTHONPATH", ""):
    import sys

    if _AITER_JIT_DIR not in sys.path:
        sys.path.insert(0, _AITER_JIT_DIR)

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM with minimal overhead."""
    A, B, B_q, B_shuffle, B_scale_sh = data

    M, K = A.shape
    N = B.shape[0]

    # Ensure A is contiguous for quant
    A_c = A.contiguous()

    # Dynamic quantize A to MXFP4
    A_q, A_scale = dynamic_mxfp4_quant(A_c)

    # Process scales - minimal operations
    num_scale_groups = K // 32
    A_scale_sh = e8m0_shuffle(A_scale[:M, :num_scale_groups].contiguous().view(dtypes.fp8_e8m0))

    # Direct GEMM dispatch
    return aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
