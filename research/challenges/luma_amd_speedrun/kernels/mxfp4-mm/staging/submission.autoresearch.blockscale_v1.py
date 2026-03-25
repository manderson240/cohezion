"""gemm_a4w4_blockscale with pre-allocated output + splitK tuning.

Key differences from gemm_a4w4:
- Requires pre-allocated Out tensor
- Has explicit splitK parameter (integer, not log2)
- No bpreshuffle flag — may not need shuffled B?
- Simpler interface: XQ, WQ, x_scale, w_scale, Out, splitK=0
"""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Pre-allocated output cache
_out_cache = {}


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M, K = A.shape
    N = B_shuffle.shape[0]

    # Quantize A
    A_q_raw, A_scale_raw = dynamic_mxfp4_quant(A)
    A_scale_shuffled = e8m0_shuffle(A_scale_raw).view(dtypes.fp8_e8m0)
    A_q = A_q_raw.view(dtypes.fp4x2)

    # Pre-allocate output
    out_key = (M, N)
    if out_key not in _out_cache:
        _out_cache[out_key] = torch.empty(M, N, dtype=torch.bfloat16, device="cuda")
    Out = _out_cache[out_key]

    # Try blockscale with shuffled B first (same as gemm_a4w4 input format)
    C = aiter.gemm_a4w4_blockscale(A_q, B_shuffle, A_scale_shuffled, B_scale_sh, Out, splitK=0)
    return C
