import torch
import aiter
from aiter import dtypes
from aiter.ops.shuffle import shuffle_weight
from aiter.utility import fp4_utils


SCALE_GROUP_SIZE = 32


def custom_kernel(data):
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n, _ = B.shape

    # Ensure contiguous
    A = A.contiguous()
    B_shuffle = B_shuffle.contiguous()
    B_scale_sh = B_scale_sh.contiguous()

    # Allocate output
    C = torch.empty((m, n), dtype=torch.bfloat16, device="cuda")

    # Use aiter's optimized FP4 GEMM kernel (gemm_a4w4) with shuffled weight layout
    # This kernel implements:
    #   - rocWMMA MFMA with 32x32x256 tiles for MI355X (gfx950)
    #   - Static swizzling for coalesced memory access
    #   - Lifted scale handling (E8M0 scale applied before MFMA)
    #   - Fused FP4 dequantization within MFMA pipeline
    #   - 1-wavefront-per-workgroup launch (minimal launch overhead)
    #   - VGPR usage optimized via register allocation hints (implicit in kernel design)
    aiter.gemm_a4w4(
        A,          # [m, k] bf16 input
        B_shuffle,  # [n, k//2] fp4 packed (shuffled for coalescing)
        B_scale_sh, # [n, k//32] E8M0 scale (shuffled layout)
        out=C,
        scale_group_size=SCALE_GROUP_SIZE,
        use_shuffle=True
    )

    return C