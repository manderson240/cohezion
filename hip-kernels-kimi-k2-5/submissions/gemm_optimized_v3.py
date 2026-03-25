"""GEMM v3: Using discovered optimal kernels."""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M, K = A.shape
    N = B.shape[0]

    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    A_q = x_fp4.view(dtypes.fp4x2)

    # Select kernel based on shape from pre-compiled kernels
    if M <= 32:
        if N <= 256:
            kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
        elif N <= 512:
            kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x256E"
        else:
            kernel_name = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x512E"
        log2_ks = 3 if M <= 8 else 2
    elif M <= 128:
        kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_128x128E"
        log2_ks = 1
    elif M <= 192:
        kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"
        log2_ks = 0
    else:
        kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_256x128E"
        log2_ks = 0

    out = torch.empty(M, N, dtype=torch.bfloat16, device="cuda")

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
