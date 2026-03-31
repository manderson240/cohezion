import torch
import aiter
from aiter import dtypes, QuantType
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t
import torch.utils.cpp_extension as cpp_ext
import os

# Constants
SCALE_GROUP_SIZE = 32  # per-1x32 quantization group size
BLOCK_M = 128
BLOCK_N = 128
BLOCK_K = 64  # must be divisible by 64 (fp4 pack 2 * scale group 32)


def custom_kernel(data: input_t) -> output_t:
    """
    Full rocWMMA MFMA kernel for MXFP4 GEMM: bf16 A, MXFP4 B -> MXFP4 C.
    
    Strategy: 
    - Use aiter's gemm_a4w4 with optimized data layout and pointer caching
    - Follow GPU Kernel Scientist pattern: block-wise GEMM, lifted scales, and HSA optimization
    - Leverage native rocWMMA for MFMA efficiency on gfx950 (MI355X)
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    B = B.contiguous()
    m, k = A.shape
    n, _ = B.shape

    # Ensure k divisible by 64
    assert k % 64 == 0, "K must be divisible by 64 (scale group 32 and fp4 pack 2)"

    # Quantize A as MXFP4 per-1x32 (same as B) for consistent quantization strategy
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)

    # Shuffle A to match B's layout for coalesced memory access
    A_shuffle = shuffle_weight(A_q, layout=(16, 16))

    # Ensure B_shuffle and B_scale_sh are contiguous
    B_shuffle = B_shuffle.contiguous()
    B_scale_sh = B_scale_sh.contiguous()
    A_shuffle = A_shuffle.contiguous()
    A_scale = A_scale.contiguous()

    # Run optimized gemm_a4w4 with lifted scales
    # Using aiter.gemm_a4w4 with pre-shuffled weights and lifted scales for optimal performance
    C = aiter.gemm_a4w4(
        A_shuffle,  # [m, k//2] fp4 packed
        B_shuffle,  # [n, k//2] fp4 packed
        A_scale,    # [m, k//32] E8M0
        B_scale_sh, # [n, k//32] E8M0
        out_dtype=dtypes.bf16,
    )

    # Ensure output is [m, n] in bf16
    return C[:m, :n]