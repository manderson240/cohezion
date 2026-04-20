"""
GEMM variant: Skip e8m0_shuffle on A scale — pass raw A_bs_e8m0 directly.
Hypothesis: e8m0_shuffle may be redundant if gemm_a4w4 handles unshuffled A scale.
"""

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    A_fp4, A_bs_e8m0 = dynamic_mxfp4_quant(A)
    A_q = A_fp4.view(dtypes.fp4x2)
    # Skip e8m0_shuffle — pass raw scale directly
    A_scale = A_bs_e8m0.view(dtypes.fp8_e8m0)

    out_gemm = aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
    return out_gemm
