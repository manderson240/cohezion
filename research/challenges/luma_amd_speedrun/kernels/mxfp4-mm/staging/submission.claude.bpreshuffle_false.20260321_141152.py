"""
GEMM variant: bpreshuffle=False with raw B_q (not B_shuffle).
Hypothesis: Different kernel path may be faster when B is not pre-shuffled.
"""

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    A_fp4, A_bs_e8m0 = dynamic_mxfp4_quant(A)
    A_q = A_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(A_bs_e8m0).view(dtypes.fp8_e8m0)

    # Use raw B_q with bpreshuffle=False — kernel does its own shuffling
    out_gemm = aiter.gemm_a4w4(
        A_q,
        B_q,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=False,
    )
    return out_gemm
