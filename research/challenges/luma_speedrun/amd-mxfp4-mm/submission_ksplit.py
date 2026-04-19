"""MXFP4 GEMM — aiter with shape-adaptive KSPLIT.

From aiter-kernel-parameter-semantics skill:
- KSPLIT controls kernel splitting strategy
- For small M (M<50 estimated_m_per_expert): KSPLIT=4 can help
- For large shapes: KSPLIT=0 or KSPLIT=2
- AITER_KSPLIT env var switches between kernel implementations

Competition shapes:
  M=4,   N=2880, K=512   -> very small M, try KSPLIT=4
  M=16,  N=2112, K=7168  -> small M, large K, try KSPLIT=2
  M=32,  N=4096, K=512   -> moderate M, try KSPLIT=2
  M=32,  N=2880, K=512   -> moderate M, try KSPLIT=2
  M=64,  N=7168, K=2048  -> moderate M, try KSPLIT=0
  M=256, N=3072, K=1536  -> large M, try KSPLIT=0
"""

import os

# Don't set KSPLIT globally — let aiter auto-select
# But DO try to ensure we use the ASM path (fastest)

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]

    # Quantize A
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)

    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
