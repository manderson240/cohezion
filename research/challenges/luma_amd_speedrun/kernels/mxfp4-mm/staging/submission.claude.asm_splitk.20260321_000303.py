"""
FP4 quant + FP4 GEMM via gemm_a4w4_asm with log2_k_split for split-K overlap.
The ASM API accepts log2_k_split unlike the generic gemm_a4w4.
"""

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    import aiter
    import torch
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    A_fp4, A_bs_e8m0 = dynamic_mxfp4_quant(A)
    A_q = A_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(A_bs_e8m0).view(dtypes.fp8_e8m0)

    M, K_half = A_q.shape
    N = B_shuffle.shape[0]
    out = torch.empty((M, N), dtype=dtypes.bf16, device=A.device)

    # Determine kernel name based on shape
    from aiter.jit.core import get_padded_m

    padded_m = get_padded_m(M, N, K_half * 2, 4)  # gl=4 for fp4
    kernel_name = f"f4gemm_bf16_per1x32Fp4_BpreShuffle_{padded_m}x128"

    aiter.gemm_a4w4_asm(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        out,
        kernel_name,
        bpreshuffle=True,
        log2_k_split=2,
    )
    return out
