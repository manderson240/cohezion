"""GEMM v2: Aggressive split-K for small M."""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M = A.shape[0]

    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    A_q = x_fp4.view(dtypes.fp4x2)

    # Aggressive: always use some split
    if M <= 4:
        log2_ks = 4  # 16-way
    elif M <= 8 or M <= 16:
        log2_ks = 3  # 8-way
    elif M <= 32 or M <= 64:
        log2_ks = 2  # 4-way
    else:
        log2_ks = 1  # 2-way

    kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
    out = torch.empty(M, B.shape[0], dtype=torch.bfloat16, device="cuda")

    return aiter.gemm_a4w4_asm(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        out,
        kernel_name,
        bpreshuffle=True,
        log2_k_split=log2_ks,
    )
