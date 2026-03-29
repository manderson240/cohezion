"""
FP4 quant + FP4 GEMM via gemm_a4w4_asm with auto kernel name selection.
Uses gemm_a4w4_asm directly (same CK kernels as gemm_a4w4 but allows log2_k_split).
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

    # Let aiter auto-select kernel name by passing empty string
    aiter.gemm_a4w4_asm(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        out,
        "",  # auto kernel selection
        bpreshuffle=True,
    )
    return out
