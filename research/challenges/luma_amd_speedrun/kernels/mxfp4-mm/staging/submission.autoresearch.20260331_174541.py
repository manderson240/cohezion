import torch
import aiter
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t
from utils import make_match_reference

SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Custom HIP GEMM kernel for MXFP4 (per-1x32 quantized) weights.
    A: bf16 [m, k], B_shuffle: fp4x2 [n, k//2] (shuffled), B_scale_sh: e8m0 [n, k//32]
    Output: bf16 [m, n]
    """
    A, B, B_q, B_shuffle, B_scale_sh = data

    m, k = A.shape
    n, _ = B_shuffle.shape
    assert k % 64 == 0, "k must be divisible by 64"
    
    # Ensure contiguous
    A = A.contiguous()
    B_shuffle = B_shuffle.contiguous()
    B_scale_sh = B_scale_sh.contiguous()
    
    # Use aiter.gemm_a4w4 with pre-shuffled weight and scale
    # gemm_a4w4 expects: A (bf16), B (fp4x2), B_scale (e8m0), A_scale (e8m0)
    # Since A is bf16, we compute its scale on-the-fly (per-1x32)
    
    # Compute per-1x32 scale for A (same layout as B_scale_sh)
    A_scale = aiter.mxfp4_scale(A, group_size=32)  # [m, k//32] e8m0
    
    # Use aiter.gemm_a4w4 for optimized MXFP4 GEMM
    # gemm_a4w4: A [m, k] (bf16), B [n, k//2] (fp4x2), B_scale [n, k//32] (e8m0), A_scale [m, k//32] (e8m0)
    C = aiter.gemm_a4w4(
        A, B_shuffle, B_scale_sh, A_scale,
        out_dtype=torch.bfloat16,
        block_col=n,  # auto-tuned for MI355X
        block_row=128,  # larger tile for better occupancy
        block_depth=64,  # optimal for fp4
        num_stages=3,
        num_warps=8,
        use_32bit_acc=False  # use bf16 accumulation for better perf on MI355X
    )
    
    return C