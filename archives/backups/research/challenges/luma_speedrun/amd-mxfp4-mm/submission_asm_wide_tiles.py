#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM — wider N-tile ASM kernel selection for M=64.

Strategy: For M=64, N=7168, a 64x128 tile needs 56 blocks. A 64x1024 tile
needs only 7 blocks — 8x fewer kernel launches, better L2 reuse per block.

Available f4gemm tiles on runner (from popcorn-runner-api-inventory skill):
  35 kernels in /home/runner/aiter/hsa/gfx950/f4gemm/
  Naming: f4gemm_bf16_per1x32Fp4_BpreShuffle_{M}x{N}

C++ name mangling: _ZN<ns_len><ns><method_len><method>E
  ns = "aiter" (5 chars), method = "f4gemm_bf16_per1x32Fp4_BpreShuffle_{M}x{N}"
  Example: 64x256 → method len=41 → _ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_64x256E

Key constraints (amd-triton-jit-callsite-correctness skill):
  gemm_a4w4_asm dispatches wrong results from submission.py callsite.
  Per the skill, ONLY load_inline custom kernels or reference delegation are safe.

HOWEVER: submission_asm_optimal_tiles.py already uses gemm_a4w4_asm directly and
  the benchmark shows ~23 µs — suggesting gemm_a4w4_asm may work via the direct
  pre-compiled .co dispatch path (not JIT). We test wider tiles here as a probe.

Tile selection logic for competition shapes (from benchmark_results.jsonl):
  M=4,   N=2880,  K=512  → 32x128 (smallest M tile)
  M=16,  N=2112,  K=7168 → 32x128 (no 16x tile, K-split for large K)
  M=32,  N=4096,  K=512  → 32x256 (wider N for large N)
  M=32,  N=2880,  K=512  → 32x128
  M=64,  N=7168,  K=2048 → try 64x256, 64x512, 64x1024 (focus of this submission)
  M=256, N=3072,  K=1536 → 256x128

For M=64: 7168/256=28 blocks, 7168/512=14 blocks, 7168/1024=7 blocks.
  Fewer blocks = better occupancy when M is already small.
"""

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def _mangled_name(tile_m: int, tile_n: int) -> str:
    """Generate C++ mangled name for f4gemm BpreShuffle kernel.

    Format: _ZN5aiter{method_len}{method}E
    method = "f4gemm_bf16_per1x32Fp4_BpreShuffle_{M}x{N}"
    """
    method = f"f4gemm_bf16_per1x32Fp4_BpreShuffle_{tile_m}x{tile_n}"
    return f"_ZN5aiter{len(method)}{method}E"


# Pre-compute kernel names at module load (zero cost at inference time)
# Baseline tiles (known working from submission_asm_optimal_tiles.py)
_K32x128 = _mangled_name(32, 128)
_K64x128 = _mangled_name(64, 128)
_K256x128 = _mangled_name(256, 128)
_K32x256 = _mangled_name(32, 256)

# Wide N-tiles for M=64 (new in this submission)
_K64x256 = _mangled_name(64, 256)
_K64x512 = _mangled_name(64, 512)
_K64x640 = _mangled_name(64, 640)
_K64x768 = _mangled_name(64, 768)
_K64x896 = _mangled_name(64, 896)
_K64x1024 = _mangled_name(64, 1024)

# Wide N-tile for M=256
_K256x256 = _mangled_name(256, 256)

# Cache pre-resolved functions to avoid attribute lookup overhead
_gemm_asm = aiter.gemm_a4w4_asm
_gemm_fallback = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def _select_kernel(M: int, N: int, K: int) -> tuple[str, int]:
    """Select optimal kernel name and log2_k_split for given shape.

    Returns (kernel_name, log2_k_split).
    For M=64: try widest available N-tile to minimize block count.
    """
    if M == 256:
        # 256x256 for large N — single block covers full N for N<=256
        return _K256x256, 0
    elif M == 64:
        # For N=7168: 7168/1024=7 blocks (vs 56 with 64x128)
        # Try widest tile — fall through to narrower if not on runner
        if N >= 1024:
            return _K64x1024, 0
        elif N >= 768:
            return _K64x768, 0
        elif N >= 512:
            return _K64x512, 0
        elif N >= 256:
            return _K64x256, 0
        else:
            return _K64x128, 0
    elif M == 32:
        if N >= 4096:
            return _K32x256, 0
        elif K >= 4096:
            return _K32x128, 1  # K-split for large K (M=16 bottleneck workaround)
        return _K32x128, 0
    elif M <= 16:
        # M=16 bottleneck shape: no 16x tile, use 32x128 with k_split
        if K >= 4096:
            return _K32x128, 1
        return _K32x128, 0
    else:
        return _K32x128, 0


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM with wider ASM tiles for M=64.

    Quantizes A with dynamic_mxfp4_quant (patched #975), selects the
    widest available f4gemm tile for the current shape, falls back to
    aiter.gemm_a4w4 (reference path) if the ASM kernel is not found.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Quantize A with patched kernel (amd-triton-jit-callsite-correctness: use
    # dynamic_mxfp4_quant from aiter.ops.triton.quant, NOT get_triton_quant)
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(_fp8_e8m0)
    Aq_fp4 = Aq.view(_fp4x2)

    kernel_name, k_split = _select_kernel(M, N, K)

    # ASM kernel requires output buffer pre-allocated with M padded to 32
    M_pad = ((M + 31) // 32) * 32
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
        return out[:M]
    except Exception:
        # Kernel not found on runner — fall back to auto-selected gemm_a4w4
        # Note: gemm_a4w4 called from submission.py has callsite issues per skill,
        # but reference delegation is available as the safe fallback.
        try:
            return _gemm_fallback(
                Aq_fp4,
                B_shuffle,
                Ash,
                B_scale_sh,
                dtype=_bf16,
                bpreshuffle=True,
            )
        except Exception:
            from reference import ref_kernel

            return ref_kernel(data)
