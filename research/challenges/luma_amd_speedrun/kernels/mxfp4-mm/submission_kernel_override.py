"""
MXFP4 GEMM with explicit kernel override.

Use gemm_a4w4_asm directly with explicit kernel name to bypass config lookup.
The kernel _ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E is used for small M values.
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


# Kernel names for different shapes (from CSV analysis)
# For M=16, use 32x128 tile kernel
KERNEL_NAME_32X128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]
    
    # Quantize A with MXFP4
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    
    # Pre-allocate output
    out = torch.empty((m, n), dtype=dtypes.bf16, device=A.device)
    
    # Call ASM path directly with explicit kernel name
    aiter.gemm_a4w4_asm(
        A_q.view(m, k // 2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        out,
        kernelName=KERNEL_NAME_32X128,
        bias=None,
        alpha=1.0,
        beta=0.0,
        bpreshuffle=True,
        log2_k_split=0,
    )
    return out
