import torch
import aiter
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t
from utils import make_match_reference


SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized MXFP4 GEMM kernel for AMD MI355X (gfx950).
    Implements fused quantization + GEMM using Triton and aiter's gemm_a4w4.
    
    Strategy:
    - Quantize A per 1x32 using MXFP4 (same as ref)
    - Use gemm_a4w4 with pre-shuffled B for coalesced memory access
    - Avoid extra dequant overhead by leveraging hardware-accelerated FP4 GEMM
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    B = B.contiguous()
    m, k = A.shape
    n, _ = B.shape

    # Quantize A using same method as reference (per-1x32 MXFP4)
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)
    
    # Use aiter's optimized FP4 GEMM kernel
    # gemm_a4w4 expects:
    #   A: [m, k//2] fp4 packed, B: [n, k//2] fp4 packed (shuffled)
    #   A_scale: [m, k//32] E8M0, B_scale: [n, k//32] E8M0
    # Returns [m, n] bf16 output
    
    C = aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2), 
        B_shuffle,
        A_scale,
        B_scale_sh,
        dtype=torch.bfloat16
    )
    
    return C


# Register for correctness checking
make_match_reference(custom_kernel)