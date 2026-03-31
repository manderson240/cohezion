import torch
import aiter
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t


SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized MXFP4 GEMM for MI355X (gfx950) using 192x128 tiling.
    A (bf16) @ B (MXFP4) -> C (bf16), with per-1x32 quantization on A.
    Uses gemm_a4w4 with 192x128 tile for M > 32.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    
    m, k = A.shape
    n, _ = B.shape
    
    # Ensure contiguous memory layout
    A = A.contiguous()
    B_shuffle = B_shuffle.contiguous()
    B_scale_sh = B_scale_sh.contiguous()
    
    # Quantize A to MXFP4 with per-1x32 scale (same as B)
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)
    
    # Convert A_scale to E8M0 format expected by gemm_a4w4
    # A_scale is already in correct layout [m, k//32]
    
    # Use gemm_a4w4 kernel with 192x128 tile for M > 32
    # Note: gemm_a4w4 expects:
    # - A: [m, k//2] fp4x2 packed (A_q)
    # - B: [n, k//2] fp4x2 packed (B_shuffle)
    # - A_scales: [m, k//32] E8M0 (A_scale)
    # - B_scales: [n, k//32] E8M0 (B_scale_sh)
    C = aiter.gemm_a4w4(
        A_q, 
        B_shuffle, 
        A_scale, 
        B_scale_sh,
        m=m,
        n=n,
        k=k,
        tile_m=192,
        tile_n=128
    )
    
    # Ensure output is contiguous and correct dtype
    return C.contiguous().to(torch.bfloat16)