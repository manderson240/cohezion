#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G2: Try gemm_a4w4_asm with explicit log2_k_split for M=16 K=7168.

The M=16 K=7168 shape is the hardest (20.9µs in aiter ref) and dominates
the geomean. K-splitting may help by parallelizing the large K dimension.

gemm_a4w4_asm signature:
  gemm_a4w4_asm(A, B, A_scale, B_scale, out, kernelName,
                bias=None, alpha=1.0, beta=0.0, bpreshuffle=True, log2_k_split=None)
"""

import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)

    # Try gemm_a4w4_asm with log2_k_split for large-K shapes
    # K=7168: log2_k_split=2 → 4 splits of K=1792 each
    # K=2048: log2_k_split=1 → 2 splits of K=1024 each
    # K=512: no split needed
    if K >= 2048:
        ksplit = 1
    else:
        ksplit = 0

    out = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    try:
        aiter.gemm_a4w4_asm(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            out,
            "",  # empty kernelName = auto-select
            None,  # bias
            1.0,  # alpha
            0.0,  # beta
            True,  # bpreshuffle
            ksplit,  # log2_k_split
        )
        return out
    except Exception:
        # Fallback to standard gemm_a4w4
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
