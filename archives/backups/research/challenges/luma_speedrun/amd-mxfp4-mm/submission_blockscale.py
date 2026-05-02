"""MXFP4 GEMM — try gemm_a4w4_blockscale path.

gemm_a4w4_blockscale might use a different (potentially faster) kernel
dispatch than gemm_a4w4 for per-1x32 MXFP4 format.
"""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    A_q, A_scale = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)

    try:
        return aiter.gemm_a4w4_blockscale(
            A_q,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
    except Exception:
        # Fallback
        return aiter.gemm_a4w4(
            A_q,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
