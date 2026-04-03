"""MXFP4 GEMM — single-call quant path for MI355X.

Key optimization: Use get_triton_quant(QuantType.per_1x32) which returns
BOTH quantized AND shuffled outputs in a single call, avoiding the
separate dynamic_mxfp4_quant + e8m0_shuffle overhead.

From aiter source analysis:
- get_triton_quant(per_1x32)(A, shuffle=True) → (A_q, A_scale_sh)
- This is the EXACT same call the reference kernel uses
- Eliminates one kernel launch (e8m0_shuffle) vs current approach

Also tries gemm_a4w4 with bpreshuffle=False path as alternative.
"""

import os

os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["AITER_GFX950_EXPL_SCHED"] = "1"

import aiter
from aiter import QuantType, dtypes
from task import input_t, output_t

# Get the combined quant+shuffle function (same as reference)
_quant_func = aiter.get_triton_quant(QuantType.per_1x32)


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Single call: quant + shuffle together (matches reference exactly)
    A_contig = A if A.is_contiguous() else A.contiguous()
    A_q, A_scale_sh = _quant_func(A_contig, shuffle=True)

    # ASM GEMM with pre-shuffled inputs
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
