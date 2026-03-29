import torch
import aiter
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t
from utils import make_match_reference

SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized GEMM for MI355X (gfx950) using 192x128 tile for M > 32.
    Implements gemm_a4w4 with MXFP4 per-1x32 quantization on both A and B.
    
    Strategy:
    - For M <= 32: fallback to standard gemm_a4w4
    - For M > 32: use gen_gemm_a4w4 with 192x128 tile
    - Handle quantization consistently with reference implementation
    - Ensure tensor contiguity and correct layouts
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    B = B.contiguous()
    m, k = A.shape
    n, _ = B.shape

    # Validate K dimension
    assert k % 64 == 0, "K must be divisible by 64 (scale group 32 and fp4 pack 2)"

    # Quantize A using MXFP4 per-1x32 (same as reference)
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)

    # For M <= 32, use default gemm_a4w4 (assumed baseline)
    if m <= 32:
        C = aiter.gemm_a4w4(
            A_q, B_shuffle, A_scale, B_scale_sh,
            out_dtype=torch.bfloat16
        )
        return C

    # For M > 32: use 192x128 tile kernel
    # Ensure B_shuffle layout is correct: [N, K//2] (already shuffled by generate_input)
    # Use gen_gemm_a4w4 with explicit tile configuration
    C = aiter.gen_gemm_a4w4(
        A_q, B_shuffle, A_scale, B_scale_sh,
        tile_m=192, tile_n=128,
        out_dtype=torch.bfloat16
    )
    
    # Ensure output shape matches expected [m, n]
    return C[:m, :n]