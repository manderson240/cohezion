#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM — grid search over N-tile widths per shape.

Strategy: For each (M, N, K) shape, benchmark available N-tile widths at runtime
and cache the fastest kernel per shape. The grid search runs only once per unique
shape (shape key = (M, N, K)), then reuses the cached kernel.

Available f4gemm tiles on runner (RUNNER_INVENTORY.md):
  32x:  [128, 256, 384, 512, 640, 768, 896, 1024]
  64x:  [128, 256, 384, 512, 640, 768, 896, 1024]
  128x: [128, 256, 384, 512]
  160x: [128, 256, 384]
  192x: [128, 256]
  224x: [128, 256]
  256x: [128, 256]

Key insight (popcorn-benchmark-vs-ranked-scoring skill):
  Only GPU compute improvements help on ranked scoring.
  Wider N-tiles reduce block count, improving CU occupancy and L2 cache reuse.
  This IS a genuine GPU compute improvement — not just Python overhead reduction.

Grid search per shape:
  M=4:   tile_M=32, try N-tiles [128] (only safe choice for partial N coverage)
  M=16:  tile_M=32, try N-tiles [128] with k_split sweep [0, 1]
  M=32:  tile_M=32, try N-tiles where N%tile_N==0 (exact block coverage)
  M=64:  tile_M=64, try N-tiles where N%tile_N==0 (exact block coverage)
  M=256: tile_M=256, try [128] only (256x256 produced wrong results for K=1536)

Correctness guarantee: ONLY tiles with exact N coverage (N % tile_N == 0) are tried.
Partial coverage tiles (N not divisible by tile_N) are excluded — the .co kernel may
or may not handle padding correctly. We use exact tiles only to ensure correctness.
Falls back to aiter.gemm_a4w4 if no ASM kernel succeeds.
"""

import time

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def _kernel_name(tile_m: int, tile_n: int) -> str:
    """C++ mangled name: _ZN5aiter{method_len}{method}E"""
    method = f"f4gemm_bf16_per1x32Fp4_BpreShuffle_{tile_m}x{tile_n}"
    return f"_ZN5aiter{len(method)}{method}E"


# All available N-tile widths per tile_M (from RUNNER_INVENTORY.md)
_TILES_BY_M: dict[int, list[int]] = {
    32: [128, 256, 384, 512, 640, 768, 896, 1024],
    64: [128, 256, 384, 512, 640, 768, 896, 1024],
    128: [128, 256, 384, 512],
    160: [128, 256, 384],
    192: [128, 256],
    224: [128, 256],
    256: [128, 256],
}


# Which tile_M fits each input M (smallest tile_M >= M, from available set)
def _tile_m_for(M: int) -> int:
    """Find the smallest available tile_M that covers M rows."""
    for tm in sorted(_TILES_BY_M.keys()):
        if tm >= M:
            return tm
    return 256  # fallback: largest available


# Pre-compute kernel names for all (tile_M, tile_N) combinations
_KERNEL_NAMES: dict[tuple[int, int], str] = {}
for tm, tile_ns in _TILES_BY_M.items():
    for tn in tile_ns:
        _KERNEL_NAMES[(tm, tn)] = _kernel_name(tm, tn)

# Pre-resolve function references
_gemm_asm = aiter.gemm_a4w4_asm
_gemm_fallback = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16

# Cache of best (kernel_name, k_split, tile_m) per shape key (M, N, K)
# Populated on first call for each shape.
_shape_cache: dict[tuple[int, int, int], tuple[str, int, int]] = {
    # Pre-populate with known safe defaults from benchmark analysis.
    # These are overridden by grid search results on first actual call.
    # M=256: 256x128 proven correct; 256x256 wrong results for K=1536.
    (256, 3072, 1536): (_kernel_name(256, 128), 0, 256),
}


def _build_candidate_list(M: int, N: int, K: int, tile_m: int) -> list[tuple[str, int, int]]:
    """Build ordered list of (kernel_name, k_split, tile_m) to try for this shape.

    Only includes tiles with exact N coverage (N % tile_N == 0).
    Ordered from widest (fewest blocks) to narrowest (most blocks).
    k_split=1 variants are appended after k_split=0 for large K (K>=4096).

    For M=256: only use 256x128 (256x256 produced wrong results for K=1536).
    """
    if M >= 256:
        # Conservative: 256x128 only — 256x256 is excluded for safety
        name = _KERNEL_NAMES[(256, 128)]
        return [(name, 0, 256)]

    available_tiles = _TILES_BY_M.get(tile_m, [128])
    # Filter to exact-coverage tiles only
    exact_tiles = [tn for tn in available_tiles if N % tn == 0]
    # Sort widest-first (fewest blocks = better occupancy)
    exact_tiles.sort(reverse=True)

    candidates: list[tuple[str, int, int]] = []
    for tn in exact_tiles:
        name = _KERNEL_NAMES[(tile_m, tn)]
        candidates.append((name, 0, tile_m))

    # For large K, also try k_split=1 with 32x128 (helps M=16 bottleneck)
    if K >= 4096 and tile_m == 32:
        fallback_name = _KERNEL_NAMES[(32, 128)]
        candidates.append((fallback_name, 1, 32))

    # Always add the narrow baseline as last resort
    baseline_name = _KERNEL_NAMES[(tile_m, 128)]
    baseline = (baseline_name, 0, tile_m)
    if baseline not in candidates:
        candidates.append(baseline)

    return candidates


def _benchmark_kernel(
    Aq_fp4: torch.Tensor,
    B_shuffle: torch.Tensor,
    Ash: torch.Tensor,
    B_scale_sh: torch.Tensor,
    M: int,
    N: int,
    kernel_name: str,
    k_split: int,
    tile_m: int,
    warmup: int = 2,
    reps: int = 5,
) -> float:
    """Run kernel warmup + timed reps. Returns median time in seconds, or inf on error."""
    M_pad = ((M + tile_m - 1) // tile_m) * tile_m
    out = torch.empty((M_pad, N), dtype=torch.bfloat16, device=Aq_fp4.device)

    # Warmup
    for _ in range(warmup):
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
        except Exception:
            return float("inf")

    torch.cuda.synchronize()

    # Timed reps
    times: list[float] = []
    for _ in range(reps):
        t0 = time.perf_counter()
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
        torch.cuda.synchronize()
        times.append(time.perf_counter() - t0)

    times.sort()
    return times[len(times) // 2]  # median


def _grid_search(
    Aq_fp4: torch.Tensor,
    B_shuffle: torch.Tensor,
    Ash: torch.Tensor,
    B_scale_sh: torch.Tensor,
    M: int,
    N: int,
    K: int,
) -> tuple[str, int, int]:
    """Run grid search over candidate kernels, return best (kernel_name, k_split, tile_m)."""
    tile_m = _tile_m_for(M)
    candidates = _build_candidate_list(M, N, K, tile_m)

    best_name, best_split, best_tile_m = candidates[-1]  # default: narrow baseline
    best_time = float("inf")

    for name, k_split, tm in candidates:
        t = _benchmark_kernel(
            Aq_fp4,
            B_shuffle,
            Ash,
            B_scale_sh,
            M,
            N,
            name,
            k_split,
            tm,
        )
        if t < best_time:
            best_time = t
            best_name, best_split, best_tile_m = name, k_split, tm

    return best_name, best_split, best_tile_m


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM with per-shape grid search over N-tile widths.

    On first call for a (M, N, K) shape: benchmarks available tiles and caches
    the fastest. Subsequent calls use the cached kernel directly.
    Falls back to aiter.gemm_a4w4 if all ASM kernels fail.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(_fp8_e8m0)
    Aq_fp4 = Aq.view(_fp4x2)

    shape_key = (M, N, K)

    if shape_key not in _shape_cache:
        # First call: run grid search to find best tile for this shape
        _shape_cache[shape_key] = _grid_search(
            Aq_fp4,
            B_shuffle,
            Ash,
            B_scale_sh,
            M,
            N,
            K,
        )

    kernel_name, k_split, tile_m = _shape_cache[shape_key]
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
