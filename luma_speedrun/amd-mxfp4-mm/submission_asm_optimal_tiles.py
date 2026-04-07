#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Optimal tile-matched .co kernel selection per shape.

INSIGHT: aiter has 35+ pre-compiled tile variants but only auto-selects
between 32x128 and 192x128. For M=64 and M=256 shapes, there are
DEDICATED tile sizes (64x128, 256x128) that eliminate thread waste.

Ranked shapes and optimal tiles:
  M=4,   N=2880,  K=512  → 32x128 (smallest available tile_M)
  M=16,  N=2112,  K=7168 → 32x128 (no 16x tile exists)
  M=32,  N=4096,  K=512  → 32x128 or 32x256 (try wider N tile)
  M=32,  N=2880,  K=512  → 32x128
  M=64,  N=7168,  K=2048 → 64x128 (PERFECT M match, no waste!)
  M=256, N=3072,  K=1536 → 256x128 (PERFECT M match, single block!)
"""

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Kernel name template
_BASE = "_ZN5aiter{}f4gemm_bf16_per1x32Fp4_BpreShuffle_{}E"


# Build mangled kernel names for different tile sizes
def _kernel_name(tile_m: int, tile_n: int) -> str:
    # C++ mangling: _ZN<ns_len><ns><method_len><method>E
    # ns = "aiter" (len=5), method = "f4gemm_bf16_per1x32Fp4_BpreShuffle_MxN"
    method = f"f4gemm_bf16_per1x32Fp4_BpreShuffle_{tile_m}x{tile_n}"
    return f"_ZN5aiter{len(method)}{method}E"


# Pre-compute kernel names
_K32x128 = _kernel_name(32, 128)
_K64x128 = _kernel_name(64, 128)
_K256x128 = _kernel_name(256, 128)
_K32x256 = _kernel_name(32, 256)
_K64x256 = _kernel_name(64, 256)
_K256x256 = _kernel_name(256, 256)

# Pre-resolve functions
_gemm_asm = aiter.gemm_a4w4_asm
_gemm = aiter.gemm_a4w4
_quant = dynamic_mxfp4_quant
_shuffle = e8m0_shuffle
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def _select_kernel(M: int, N: int, K: int) -> tuple[str, int]:
    """Select optimal kernel tile and k_split for this shape."""
    # Try M-matched tiles first (best CU utilization)
    if M == 256:
        return _K256x128, 0
    elif M == 64:
        return _K64x128, 0
    elif M == 32 and N >= 4096:
        return _K32x256, 0  # Wider N tile for large N
    elif M <= 32:
        if K >= 4096:
            return _K32x128, 1  # K-split for large K
        return _K32x128, 0
    else:
        return _K32x128, 0


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Quantize A
    Aq, Asc = _quant(A.contiguous())
    Ash = _shuffle(Asc).view(_fp8_e8m0)

    # Select optimal kernel
    kernel_name, k_split = _select_kernel(M, N, K)

    # Pad output for ASM kernel requirement
    M_pad = ((M + 31) // 32) * 32
    out = torch.empty((M_pad, N), dtype=torch.bfloat16, device=A.device)

    try:
        _gemm_asm(
            Aq.view(_fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            out,
            kernel_name,
            bpreshuffle=True,
            log2_k_split=k_split,
        )
        return out[:M]
    except Exception:
        # Fallback to standard gemm_a4w4 if kernel name not found on runner
        return _gemm(
            Aq.view(_fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=_bf16,
            bpreshuffle=True,
        )
