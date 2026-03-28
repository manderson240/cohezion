"""
MXFP4 GEMM - Compound Engineering Optimization

Key optimizations:
1. REUSE B_scale_sh from task input (no recomputation needed)
2. Only quantize A with dynamic_mxfp4_quant
3. Use correct gemm_a4w4 path with bpreshuffle=True

This compound approach uses the pre-shuffled B_scale that comes
from the task input, eliminating the need for any B_scale computation.
"""

from __future__ import annotations

import os
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
import aiter
from task import input_t, output_t


os.environ["HIP_ONLINE_TUNING"] = "1"


def custom_kernel(data: input_t) -> output_t:
    """
    Compound MXFP4 GEMM with B scale reuse.

    Input tuple: (A, B, B_q, B_shuffle, B_scale_sh)
    - A: bf16 [M, K]
    - B: bf16 [N, K]
    - B_q: MXFP4 [N, K//2] - quantized B (REUSE THIS)
    - B_shuffle: MXFP4 [N, K//2] - B_q with e8m0_shuffle applied
    - B_scale_sh: E8M0 [* , K//32] - scale with e8m0_shuffle applied

    Key insight: B_scale_sh is already shuffled. The gemm_a4w4 with
    bpreshuffle=True expects shuffled scales and handles everything.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data

    m, k = A.shape

    # Quantize A with MXFP4 (main cost ~10-15µs)
    A_fp4, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_q = A_fp4.view(dtypes.fp4x2)

    # Shuffle A_scale inline
    A_scale_u8 = A_scale_e8m0[:m, :].contiguous().view(dtypes.fp8_e8m0)
    A_scale_sh = e8m0_shuffle(A_scale_u8)

    # Call GEMM - reuse B_q and B_scale_sh from task input
    out = aiter.gemm_a4w4(
        A_q,
        B_shuffle,  # Use shuffled B
        A_scale_sh,
        B_scale_sh,  # Use shuffled scale
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )

    return out
