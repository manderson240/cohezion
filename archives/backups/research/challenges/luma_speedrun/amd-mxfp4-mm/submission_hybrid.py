"""MXFP4 GEMM — hybrid aiter path with shape-aware dispatch.

Use aiter gemm_a4w4 for all shapes (proven fastest overall).
Skip .contiguous() since A comes from generate_input already contiguous.
Use @torch.no_grad() to skip autograd.
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

    # Quantize A — this is the bottleneck (~12-15µs)
    A_q, A_scale = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)

    # aiter ASM path — fastest for all shapes
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
