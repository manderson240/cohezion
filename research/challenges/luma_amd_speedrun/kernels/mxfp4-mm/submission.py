"""
MXFP4 GEMM — Uses dynamic_mxfp4_quant with e8m0_shuffle.
Optimized path from gemm-specialist submission.
"""
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized MXFP4 GEMM with direct Triton quantization path.
    """
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data

    # Ensure A is contiguous for quantization
    A = A.contiguous()
    m, k = A.shape

    # Quantize A using direct Triton kernel
    A_fp4, A_scale = dynamic_mxfp4_quant(A)

    # Prepare shuffled scale for GEMM
    A_scale_u8 = A_scale[:m, :].contiguous().view(dtypes.fp8_e8m0)
    A_scale_sh = e8m0_shuffle(A_scale_u8)

    # A_fp4 is uint8 view of packed FP4
    A_q = A_fp4.view(dtypes.fp4x2)

    # Call gemm_a4w4 with pre-shuffled B and B_scale
    out_gemm = aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
    return out_gemm
