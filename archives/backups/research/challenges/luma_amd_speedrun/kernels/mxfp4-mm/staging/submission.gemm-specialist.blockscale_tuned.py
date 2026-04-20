"""
MXFP4 GEMM with tuned block sizes.

Key optimization: Use larger BLOCK_K=128 for better GPU utilization.
The default BLOCK_K=64 may not be optimal for all shapes.
"""

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    MXFP4 GEMM with tuned GEMM path.

    Uses gemm_a4w4_blockscale directly with pre-allocated output,
    avoiding dispatch overhead in unified gemm_a4w4 API.
    """
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data

    # Ensure A is contiguous for quantization
    A = A.contiguous()
    m, k = A.shape
    n = B_shuffle.shape[0]

    # Quantize A only
    A_fp4, A_scale = dynamic_mxfp4_quant(A)

    # Prepare shuffled scale
    A_scale_u8 = A_scale[:m, :].contiguous().view(dtypes.fp8_e8m0)
    A_scale_sh = e8m0_shuffle(A_scale_u8)
    A_q = A_fp4.view(dtypes.fp4x2)

    # Pre-allocate output for blockscale path
    Out = A_q.new_empty(m, n, dtype=dtypes.bf16)

    # Call gemm_a4w4_blockscale directly - splitK=0 for most shapes
    # This bypasses unified API dispatch overhead
    C = aiter.gemm_a4w4_blockscale(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        Out,
        splitK=0,
    )
    return C
