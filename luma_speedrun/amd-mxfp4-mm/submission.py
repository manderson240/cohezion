"""MXFP4 GEMM submission — single-call quant for MI355X (gfx950).

Optimizations:
1. get_triton_quant(per_1x32) — single call for quant+shuffle (matches reference)
2. Env vars: USE_NT, BYPASS_TUNE_CONFIG, GFX950_EXPL_SCHED
3. Skip contiguous() if already contiguous

Uses the EXACT same quant call as the official reference kernel.
Eliminates separate e8m0_shuffle kernel launch.
"""

import os

os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["AITER_GFX950_EXPL_SCHED"] = "1"

import aiter
from aiter import QuantType, dtypes
from task import input_t, output_t

_quant_func = aiter.get_triton_quant(QuantType.per_1x32)


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    # Single-call quant+shuffle (same as reference kernel)
    A_contig = A if A.is_contiguous() else A.contiguous()
    A_q, A_scale_sh = _quant_func(A_contig, shuffle=True)
    # ASM GEMM — uses pre-compiled .co kernels on MI355X
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
