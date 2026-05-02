"""MXFP4 GEMM — try tritonblas.matmul_fp4 path.

From tritonblas-matmul-fp4-api skill:
- All tensors MUST be torch.uint8 views
- B layout is [N, K//2] row-major (NOT transposed like aiter)
- Output C must be pre-allocated and passed as 3rd positional argument
- Uses Triton JIT under the hood — may be faster for some shapes
"""

import torch
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]

    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from aiter.utility.fp4_utils import e8m0_shuffle
        from tritonblas import matmul_fp4

        # Quantize A
        A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())

        # tritonblas needs uint8 views, un-shuffled
        A_packed = A_q.view(torch.uint8)
        A_scale_bytes = A_scale.view(torch.uint8)

        # B_q is already [N, K/2] from generate_input
        B_packed = B_q.view(torch.uint8)

        # Need un-shuffled B scale — re-quantize B to get it
        _, B_scale_raw = dynamic_mxfp4_quant(B.contiguous())
        B_scale_bytes = B_scale_raw.view(torch.uint8)

        # Pre-allocate output
        C = torch.empty((m, n), dtype=torch.bfloat16, device=A.device)

        # tritonblas matmul_fp4: (A, B, C, A_scale, B_scale)
        matmul_fp4(A_packed, B_packed, C, A_scale_bytes, B_scale_bytes)
        return C

    except Exception:
        # Fallback to aiter
        import aiter
        from aiter import dtypes

        A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())
        A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
        A_q = A_q.view(dtypes.fp4x2)
        return aiter.gemm_a4w4(
            A_q,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
