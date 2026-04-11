"""
MXFP4 GEMM with optimized quantization path.

Key optimization: B is already pre-quantized in task input (B_q, B_shuffle, B_scale_sh).
Only quantize A using direct Triton path, avoiding overhead in aiter's unified API.

Direct Triton kernel invocation bypasses some dispatch overhead.
"""

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized MXFP4 GEMM with direct Triton path.

    Input: (A, B, B_q, B_shuffle, B_scale_sh)
    - A: bf16 [M, K] - needs quantization
    - B: bf16 [N, K] - NOT USED (already quantized in B_q)
    - B_q: MXFP4 [N, K/2] - pre-quantized
    - B_shuffle: shuffled MXFP4 [N, K/2] - for GEMM
    - B_scale_sh: E8M0 [*, K/32] - pre-shuffled scales for B

    The key insight is that we ONLY quantize A, and use the pre-shuffled B directly.
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
    k_half = k // 2

    # Quantize A only - this is the key overhead we're working with
    # Use direct Triton kernel instead of aiter.get_triton_quant wrapper
    A_fp4, A_scale = dynamic_mxfp4_quant(A)

    # Prepare shuffled scale for GEMM (same as B_scale_sh layout)
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
