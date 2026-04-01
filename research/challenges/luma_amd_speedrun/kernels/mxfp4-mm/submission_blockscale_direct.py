"""
MXFP4 GEMM with forced block-scale path.

Key insight: Force the gemm_a4w4_blockscale path which uses CK kernels
instead of the ASM path which has no tuned config for M=16, N=2112, K=7168.

The blockscale kernel can be selected by passing a valid kernel config.
"""

from __future__ import annotations

import os


# Enable HIP online tuning BEFORE importing aiter
os.environ["HIP_ONLINE_TUNING"] = "1"

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]
    
    # Quantize A with MXFP4
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    
    # Try blockscale path first (CK kernels have better support for varied shapes)
    try:
        Out = torch.empty((m, n), dtype=dtypes.bf16, device=A.device)
        return aiter.gemm_a4w4_blockscale(
            A_q.view(m, k // 2),
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            Out,
            splitK=0,
        )[:m]
    except Exception as e:
        # Fallback to unified gemm_a4w4 if blockscale fails
        return aiter.gemm_a4w4(
            A_q, B_shuffle, A_scale_sh, B_scale_sh,
            dtype=dtypes.bf16, bpreshuffle=True,
        )
