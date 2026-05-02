"""MXFP4 GEMM — tritonblas.matmul_fp4 with pre-quantized B.

Key insight: B_q from generate_input is ALREADY quantized MXFP4.
Don't re-quantize B! Use B_q directly.

But: tritonblas needs un-shuffled data, and B_q uses aiter's fp4x2 format.
B_scale_sh is shuffled. Need to probe if tritonblas can use them directly.

From tritonblas-matmul-fp4-api skill:
- All tensors MUST be torch.uint8 views
- B layout is [N, K//2] row-major
"""

import sys

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]

    # Quantize A (unavoidable — A is bf16)
    A_q, A_scale = dynamic_mxfp4_quant(A)

    try:
        from tritonblas import matmul_fp4

        # A as uint8
        A_packed = A_q.view(torch.uint8)
        A_scale_bytes = A_scale.view(torch.uint8)

        # B_q is [N, K/2] in fp4x2 format from generate_input
        # It was quantized with shuffle=True, so it's aiter-shuffled
        # Try using it directly as uint8
        B_packed = B_q.view(torch.uint8)
        B_scale_bytes = B_scale_sh.view(torch.uint8)

        # Pre-allocate output
        C = torch.empty((m, n), dtype=torch.bfloat16, device=A.device)

        matmul_fp4(A_packed, B_packed, C, A_scale_bytes, B_scale_bytes)
        return C
    except Exception as e:
        print(f"PROBE: tritonblas failed: {e}", file=sys.stderr)
        # Fallback
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
