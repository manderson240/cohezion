"""MXFP4 GEMM — try deepgemm_ck path (CK-based, potentially fused).

deepgemm_ck was found available on the runner. It might use the CK Flatmm
pipeline with persistent async scheduling — potentially faster than ASM for
some shapes.
"""

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]

    A_q, A_scale = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)

    # Try deepgemm_ck first
    try:
        result = aiter.deepgemm_ck(
            A_q,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            dtype=dtypes.bf16,
        )
        return result
    except Exception as e:
        pass

    # Try with different arg patterns
    try:
        out = torch.empty((m, n), dtype=torch.bfloat16, device=A.device)
        result = aiter.deepgemm_ck(
            A_q,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            out,
        )
        return out
    except Exception:
        pass

    # Fallback to standard gemm_a4w4
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
