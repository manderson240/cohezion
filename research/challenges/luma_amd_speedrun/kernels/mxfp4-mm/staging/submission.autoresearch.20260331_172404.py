import aiter
import torch
from aiter import QuantType, dtypes
from task import input_t, output_t


SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Block-scale GEMM for MXFP4 (A: bf16, B: MXFP4 w/ block scales).
    Uses aiter.gemm_a4w4 with block-scale support (NOT tuned_gemm path).
    A is quantized per-1x32 to MXFP4; B is already MXFP4 with shuffled layout.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    B_shuffle = B_shuffle.contiguous()
    B_scale_sh = B_scale_sh.contiguous()

    m, k = A.shape
    n, _ = B_shuffle.shape

    # Quantize A to MXFP4 per-1x32 (same as reference)
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)
    
    # Convert FP4x2 packed tensors to expected uint8 view for aiter.gemm_a4w4
    # aiter.gemm_a4w4 expects dtypes.fp4x2 input as torch.uint8 (view)
    A_q_uint8 = A_q.view(torch.uint8)
    B_q_uint8 = B_q.view(torch.uint8)

    # Ensure scales are contiguous and in correct shape
    A_scale = A_scale.contiguous()
    B_scale_sh = B_scale_sh.contiguous()

    # Run block-scale GEMM: uses gemm_a4w4 with block-scale support (NOT tuned_gemm)
    # Layout: A [m, k], B [n, k] -> C [m, n]
    # gemm_a4w4 expects:
    #   A: [m, k] (bf16 or fp4x2), B: [n, k] (fp4x2)
    #   A_scale: [m, k//32], B_scale: [n, k//32]
    #   layout: A_scale/B_scale in row-major, matching fp4 packing
    C = aiter.gemm_a4w4(
        A_q_uint8 if A_q.dtype == dtypes.fp4x2 else A,
        B_shuffle,
        A_scale,
        B_scale_sh,
        dtype=torch.bfloat16,
        block_scale=True  # Enable block-scale path (NOT tuned_gemm)
    )

    # Ensure output shape correctness (m x n)
    return C[:m, :n]