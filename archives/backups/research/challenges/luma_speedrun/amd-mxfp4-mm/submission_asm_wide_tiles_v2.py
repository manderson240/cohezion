#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM — wider N-tile ASM kernel selection (v2, M=256 fixed).

Fix from v1: M=256 used 256x256 tile which produces wrong results for K=1536.
Root cause: 256x256 tile may require K to be a multiple of a larger stride than
256x128 tile. Fix: use 256x128 for M=256 (matches submission_asm_optimal_tiles.py
which passed), use 256x256 only when N is large enough to benefit AND K is safe.

Strategy per shape (from RUNNER_INVENTORY.md — 35 .co files on runner):
  M=4,   N=2880,  K=512  → tile_M=32, 32x128 (smallest tile_M available)
  M=16,  N=2112,  K=7168 → tile_M=32, 32x128 with k_split=1 (large K)
  M=32,  N=4096,  K=512  → tile_M=32, 32x512 (N divisible by 512, exact blocks)
  M=32,  N=2880,  K=512  → tile_M=32, 32x128 (N not cleanly divisible by large tiles)
  M=64,  N=7168,  K=2048 → tile_M=64, 64x1024 (7 exact blocks vs 56 for 64x128)
  M=256, N=3072,  K=1536 → tile_M=256, 256x128 (24 exact blocks, proven correct)

Padding rule: output tensor is padded to ceil(M/tile_M)*tile_M rows.
  tile_M=32 → pad to next multiple of 32
  tile_M=64 → pad to next multiple of 64
  tile_M=256 → pad to next multiple of 256
"""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def _kernel_name(tile_m: int, tile_n: int) -> str:
    """C++ mangled name for f4gemm BpreShuffle kernel.

    Format: _ZN5aiter{method_len}{method}E
    method = 'f4gemm_bf16_per1x32Fp4_BpreShuffle_{tile_m}x{tile_n}'
    """
    method = f"f4gemm_bf16_per1x32Fp4_BpreShuffle_{tile_m}x{tile_n}"
    return f"_ZN5aiter{len(method)}{method}E"


# Pre-compute kernel names for competition shapes
# tile_M=32 group (handles M=4, M=16, M=32)
_K32x128 = _kernel_name(32, 128)
_K32x256 = _kernel_name(32, 256)
_K32x512 = _kernel_name(32, 512)
_K32x1024 = _kernel_name(32, 1024)

# tile_M=64 group (handles M=64)
_K64x128 = _kernel_name(64, 128)
_K64x256 = _kernel_name(64, 256)
_K64x512 = _kernel_name(64, 512)
_K64x1024 = _kernel_name(64, 1024)

# tile_M=256 group (handles M=256)
# 256x128 is proven correct for M=256, N=3072, K=1536
# 256x256 is NOT used here — it failed for K=1536 in v1
_K256x128 = _kernel_name(256, 128)

# Pre-resolve function references (avoids attribute lookup at call time)
_gemm_asm = aiter.gemm_a4w4_asm
_gemm_fallback = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def _select_kernel(M: int, N: int, K: int) -> tuple[str, int, int]:
    """Select optimal kernel name, log2_k_split, and tile_M for given shape.

    Returns (kernel_name, log2_k_split, tile_m).
    tile_m is used to compute the output padding requirement.

    Selection priority: use the widest N-tile that gives exact block coverage
    (N % tile_N == 0), fallback to 32x128/64x128/256x128 which always handle
    partial blocks correctly.
    """
    if M >= 256:
        # M=256, N=3072, K=1536 → 256x128: 3072/128=24 exact blocks
        # 256x128 proven correct; 256x256 failed for K=1536 in v1
        return _K256x128, 0, 256

    elif M >= 64:
        # M=64, N=7168, K=2048 → 64x1024: 7168/1024=7 exact blocks
        # Fewer blocks = better: 7 vs 56 (64x128) = 8x fewer launches
        if N % 1024 == 0:
            return _K64x1024, 0, 64
        elif N % 512 == 0:
            return _K64x512, 0, 64
        elif N % 256 == 0:
            return _K64x256, 0, 64
        else:
            return _K64x128, 0, 64

    else:
        # M <= 32: use tile_M=32 (smallest available)
        # M=32, N=4096, K=512 → 32x512: 4096/512=8 exact blocks
        # M=32, N=2880, K=512 → 32x128 (2880 not divisible by 256/512/1024)
        # M=16, N=2112, K=7168 → 32x128 with k_split (K large, use split)
        # M=4,  N=2880, K=512  → 32x128

        if K >= 4096:
            # Large K: k_split=1 helps distribute the K reduction
            return _K32x128, 1, 32

        if N % 1024 == 0:
            return _K32x1024, 0, 32
        elif N % 512 == 0:
            return _K32x512, 0, 32
        elif N % 256 == 0:
            return _K32x256, 0, 32
        else:
            return _K32x128, 0, 32


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM with tile-matched ASM kernels.

    Selects the widest N-tile with exact block coverage for the current shape.
    Output tensor is padded to tile_M boundary and sliced back to M rows.
    Falls back to aiter.gemm_a4w4 if the ASM kernel fails.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(_fp8_e8m0)
    Aq_fp4 = Aq.view(_fp4x2)

    kernel_name, k_split, tile_m = _select_kernel(M, N, K)

    # Pad output to tile_M boundary — kernel writes tile_M rows per block
    M_pad = ((M + tile_m - 1) // tile_m) * tile_m
    out = torch.empty((M_pad, N), dtype=torch.bfloat16, device=A.device)

    try:
        _gemm_asm(
            Aq_fp4,
            B_shuffle,
            Ash,
            B_scale_sh,
            out,
            kernel_name,
            bpreshuffle=True,
            log2_k_split=k_split,
        )
        return out[:M].contiguous()
    except Exception:
        return _gemm_fallback(
            Aq_fp4,
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=_bf16,
            bpreshuffle=True,
        )
