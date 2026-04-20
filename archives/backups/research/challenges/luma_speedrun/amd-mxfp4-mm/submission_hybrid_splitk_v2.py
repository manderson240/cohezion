#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Hybrid split-K GEMM v2: aiter for 5 of 6 ranked shapes, split-K for M=16 K>=4096.

Root cause analysis of v1 (submission_triton_splitk.py) scoring 23µs vs aiter baseline 13.4µs:

The v1 submission defined two @triton.jit kernels (fp4_gemm_splitk_kernel,
fp4_reduce_kernel) at MODULE LEVEL. On AMD MI355X, Triton JIT compilation for
gfx950 kernels is slow (several hundred milliseconds). The benchmark runner
measures warm-call latency, but the Triton XCD-remapping and JIT registry
overhead from having those kernel objects loaded interferes with the CK ASM
kernel that aiter uses internally.

Evidence: v1 aiter-path shapes (M=4,32,64,256) showed 19-24µs instead of 8-12µs.
The aiter CK kernel itself is unchanged. The overhead must come from the Triton
module-level state.

Fix: ALL Triton kernel definitions are moved INSIDE a lazy-init function that
only runs when the split-K path is triggered (M<=16 and K>=4096). The module-level
import footprint for the 5 aiter-path shapes is identical to the pure aiter
baseline (submission_naive_13us.py style).

Ranked shapes (from RANKED_SHAPES.md):
  M=4,   N=2880, K=512   -> use_splitk=False (K<4096)   -> aiter
  M=16,  N=2112, K=7168  -> use_splitk=True              -> split-K Triton
  M=32,  N=4096, K=512   -> use_splitk=False (M>16)      -> aiter
  M=32,  N=2880, K=512   -> use_splitk=False (M>16)      -> aiter
  M=64,  N=7168, K=2048  -> use_splitk=False (M>16)      -> aiter
  M=256, N=3072, K=1536  -> use_splitk=False (M>16)      -> aiter

The split-K path is only triggered for exactly 1 of 6 ranked shapes. The other
5 shapes must run at pure-aiter speed (8-12µs) for the geomean to improve.

Geomean target:
  aiter baseline: geom(8.2, 20.8, 9.5, 9.2, 12.7, 12.2) ≈ 11.3µs
  v2 target:      geom(8.2, ~15,  9.5, 9.2, 12.7, 12.2) ≈ 10.5µs (if split-K helps M=16)

Split-K rationale for M=16, K=7168:
  Standard: 17 tiles (1 M-tile * 17 N-tiles) -> 17/304 = 6% CU occupancy
  Split-K K_SPLITS=8: 136 programs -> 45% occupancy, K-work parallelised
"""

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# ---------------------------------------------------------------------------
# Lazy split-K module: compiled once on first use of the split-K path.
# Keeping all Triton state here prevents module-level JIT registration from
# interfering with the aiter CK kernel on the 5 non-split-K shapes.
# ---------------------------------------------------------------------------

_splitk_module = None  # populated on first split-K call


def _get_splitk_module():
    """Build and cache the split-K Triton kernel module on first invocation.

    Uses a nested function to ensure the @triton.jit decorated kernels are
    only registered with the Triton runtime when the split-K path is needed.
    The module-level import of triton itself is deferred to this function.
    """
    global _splitk_module
    if _splitk_module is not None:
        return _splitk_module

    import triton
    import triton.language as tl

    @triton.jit
    def fp4_gemm_splitk_kernel(
        # Pointers
        A_ptr,  # [M, K//2]  uint8, FP4x2 packed, row-major
        B_t_ptr,  # [K//2, N]  uint8, FP4x2 packed, B transposed (K-major)
        As_ptr,  # [M, K//32] uint8, E8M0 A scales
        Bs_ptr,  # [N, K//32] uint8, E8M0 B scales (N-first layout for gfx950)
        Partial_ptr,  # [M, N]  float32, atomic accumulation buffer
        # Dimensions
        M,
        N,
        K,
        K_per_split,  # number of FP4 elements this split processes (multiple of BLOCK_K)
        # Strides for A [M, K//2]
        stride_am,
        stride_ak,
        # Strides for B_t [K//2, N]
        stride_bk,
        stride_bn,
        # Strides for Partial [M, N]
        stride_pm,
        stride_pn,
        # Strides for As [M, K//32]
        stride_asm,
        stride_ask,
        # Strides for Bs [N, K//32]
        stride_bsn,
        stride_bsk,
        # Tile sizes (constexpr)
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        """One Triton program handles one (M-tile, N-tile, K-split).

        Computes partial dot product for K_per_split elements starting at
        k_split_start = pid_k * K_per_split, then atomic-adds into Partial_ptr.

        BLOCK_K >= 128 enforced by caller — BLOCK_K=64 silently corrupts on gfx950.
        """
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        pid_k = tl.program_id(2)  # which K-split this program handles

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

        # Byte and scale-group widths for a single BLOCK_K tile
        K_bytes: tl.constexpr = BLOCK_K // 2  # bytes consumed per K-tile (2 FP4 per byte)
        K_sg: tl.constexpr = BLOCK_K // 32  # scale groups per K-tile

        K_total_bytes = K // 2
        K_total_sg = K // 32

        # Where this split starts in FP4-element space
        k_split_start = pid_k * K_per_split

        # How many BLOCK_K tiles this split covers
        k_split_bytes_start = k_split_start // 2  # in bytes
        num_k_iters = K_per_split // BLOCK_K  # exact multiple guaranteed by caller

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for k_iter in range(num_k_iters):
            # Absolute byte offset into A/B_t for this BLOCK_K tile
            k_byte_off = k_split_bytes_start + k_iter * K_bytes
            k_sg_off = k_split_start // 32 + k_iter * K_sg

            offs_kb = k_byte_off + tl.arange(0, K_bytes)
            offs_sg = k_sg_off + tl.arange(0, K_sg)

            # Load A tile: [BLOCK_M, K_bytes]
            a_mask = (offs_m[:, None] < M) & (offs_kb[None, :] < K_total_bytes)
            a = tl.load(
                A_ptr + offs_m[:, None] * stride_am + offs_kb[None, :] * stride_ak,
                mask=a_mask,
                other=0,
            )

            # Load B_t tile: [K_bytes, BLOCK_N] (K-major, transposed B)
            b_mask = (offs_kb[:, None] < K_total_bytes) & (offs_n[None, :] < N)
            b = tl.load(
                B_t_ptr + offs_kb[:, None] * stride_bk + offs_n[None, :] * stride_bn,
                mask=b_mask,
                other=0,
            )

            # Load A scales: [BLOCK_M, K_sg]
            as_mask = (offs_m[:, None] < M) & (offs_sg[None, :] < K_total_sg)
            a_scale = tl.load(
                As_ptr + offs_m[:, None] * stride_asm + offs_sg[None, :] * stride_ask,
                mask=as_mask,
                other=127,
            )

            # Load B scales: [BLOCK_N, K_sg] — N-first required by gfx950
            bs_mask = (offs_n[:, None] < N) & (offs_sg[None, :] < K_total_sg)
            b_scale = tl.load(
                Bs_ptr + offs_n[:, None] * stride_bsn + offs_sg[None, :] * stride_bsk,
                mask=bs_mask,
                other=127,
            )

            # MXFP4 scaled dot product — requires BLOCK_K >= 128 on gfx950
            acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc)

        # Atomic-add partial results into float32 accumulator buffer.
        # Different pid_k values race on the same output cells — hence atomic.
        c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        partial_ptrs = Partial_ptr + offs_m[:, None] * stride_pm + offs_n[None, :] * stride_pn
        tl.atomic_add(partial_ptrs, acc, mask=c_mask)

    @triton.jit
    def fp4_reduce_kernel(
        Partial_ptr,  # [M, N] float32
        C_ptr,  # [M, N] bfloat16
        M,
        N,
        stride_pm,
        stride_pn,
        stride_cm,
        stride_cn,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        """Convert accumulated float32 partial sums to bfloat16 output."""
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

        mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

        partial = tl.load(
            Partial_ptr + offs_m[:, None] * stride_pm + offs_n[None, :] * stride_pn,
            mask=mask,
            other=0.0,
        )
        tl.store(
            C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn,
            partial.to(tl.bfloat16),
            mask=mask,
        )

    _splitk_module = (triton, fp4_gemm_splitk_kernel, fp4_reduce_kernel)
    return _splitk_module


# ---------------------------------------------------------------------------
# Weight layout helpers (only used on split-K path)
# ---------------------------------------------------------------------------


def _e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to recover [orig_m, orig_n] E8M0 layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def _choose_splitk_config(M: int, K: int) -> tuple[int, int, int, int]:
    """Choose BLOCK_M, BLOCK_N, BLOCK_K, K_SPLITS for the split-K path.

    Rules:
    - BLOCK_K=128 always (gfx950 minimum for tl.dot_scaled; maximises K_SPLITS)
    - K_SPLITS: largest power-of-2 that evenly divides K//BLOCK_K
    - MI355X has 304 CUs

    For M=16, K=7168, BLOCK_N=128:
      total_k_tiles = 7168/128 = 56
      K_SPLITS=8: 7 tiles/split; grid = 1*17*8 = 136 programs -> 44.7% CU use
    """
    BLOCK_K = 128
    BLOCK_M = 16 if M <= 16 else (32 if M <= 32 else 64)
    BLOCK_N = 128
    total_k_tiles = K // BLOCK_K
    for splits in [16, 8, 4, 2, 1]:
        if total_k_tiles % splits == 0:
            K_SPLITS = splits
            break
    else:
        K_SPLITS = 1
    return BLOCK_M, BLOCK_N, BLOCK_K, K_SPLITS


# Partial-sum buffer cache: keyed by (M, N) -> float32 tensor
_partial_cache: dict = {}
# Weight cache: keyed by (B_scale_sh.data_ptr, N, ks) -> (B_t, Bs_bytes)
_weight_cache: dict = {}


def _run_splitk_gemm(
    A_bytes: torch.Tensor,  # [M, K//2] uint8
    B_t: torch.Tensor,  # [K//2, N] uint8
    As_bytes: torch.Tensor,  # [M, K//32] uint8
    Bs_bytes: torch.Tensor,  # [N, K//32] uint8
    M: int,
    N: int,
    K: int,
) -> torch.Tensor:
    """Launch split-K GEMM: accumulate into float32, then reduce to bfloat16."""
    triton, fp4_gemm_splitk_kernel, fp4_reduce_kernel = _get_splitk_module()

    BLOCK_M, BLOCK_N, BLOCK_K, K_SPLITS = _choose_splitk_config(M, K)
    K_per_split = K // K_SPLITS  # FP4 elements per split; exact multiple of BLOCK_K

    # Partial accumulator (float32) — reuse across calls to avoid allocation overhead
    buf_key = (M, N)
    if buf_key not in _partial_cache:
        _partial_cache.clear()
        _partial_cache[buf_key] = torch.zeros((M, N), dtype=torch.float32, device=A_bytes.device)
    partial = _partial_cache[buf_key]
    partial.zero_()  # reset before each call (atomic_add accumulates)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A_bytes.device)

    num_m_tiles = triton.cdiv(M, BLOCK_M)
    num_n_tiles = triton.cdiv(N, BLOCK_N)
    splitk_grid = (num_m_tiles, num_n_tiles, K_SPLITS)

    fp4_gemm_splitk_kernel[splitk_grid](
        A_bytes,
        B_t,
        As_bytes,
        Bs_bytes,
        partial,
        M,
        N,
        K,
        K_per_split,
        A_bytes.stride(0),
        A_bytes.stride(1),
        B_t.stride(0),
        B_t.stride(1),
        partial.stride(0),
        partial.stride(1),
        As_bytes.stride(0),
        As_bytes.stride(1),
        Bs_bytes.stride(0),
        Bs_bytes.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )

    reduce_grid = (num_m_tiles, num_n_tiles)
    fp4_reduce_kernel[reduce_grid](
        partial,
        C,
        M,
        N,
        partial.stride(0),
        partial.stride(1),
        C.stride(0),
        C.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
    )

    return C


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM hybrid: aiter for 5 of 6 ranked shapes, split-K for M<=16 K>=4096.

    Performance strategy:
    - The 5 aiter shapes (M=4,32,32,64,256) run at pure-aiter speed (8-12µs).
      No Triton state is touched on these paths — the @triton.jit kernels are
      defined lazily inside _get_splitk_module() and never compiled unless M=16.
    - The M=16 K=7168 shape triggers split-K Triton on first call (JIT compiles
      once, ~300ms), then runs at split-K speed on subsequent calls.
    - Benchmark runner warms up before timing — JIT cost is amortised.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    use_splitk = M <= 16 and K >= 4096

    if use_splitk:
        # Quantize A for the Triton split-K path
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())

        A_bytes = Aq.view(torch.uint8)  # [M, K//2]
        As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)  # [M, ks]

        # B weight and scales are constant across inference calls — cache
        cache_key = (B_scale_sh.data_ptr(), N, ks)
        if cache_key not in _weight_cache:
            _weight_cache.clear()
            B_bytes = B_q.view(torch.uint8)  # [N, K//2]
            B_t = B_bytes.t().contiguous()  # [K//2, N] K-major for tl.dot_scaled
            Bs_unshuffled = _e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks)
            Bs_bytes = Bs_unshuffled.contiguous().view(torch.uint8)  # [N, ks]
            _weight_cache[cache_key] = (B_t, Bs_bytes)

        B_t, Bs_bytes = _weight_cache[cache_key]

        try:
            return _run_splitk_gemm(A_bytes, B_t, As_bytes, Bs_bytes, M, N, K)
        except Exception as exc:
            # Defensive fallback: if split-K fails, fall through to aiter below
            print(
                f"[hybrid_splitk_v2] split-K failed, falling back to aiter: {exc!s:.200}",
                flush=True,
            )
            # Re-quantize for aiter path (Aq/Asc are already computed above, reuse)
            Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
            return aiter.gemm_a4w4(
                Aq.view(dtypes.fp4x2),
                B_shuffle,
                Ash,
                B_scale_sh,
                dtype=dtypes.bf16,
                bpreshuffle=True,
            )

    # Pure aiter path: handles M=4,32,64,256 shapes (5 of 6 ranked shapes).
    # This path is IDENTICAL to the 13.4µs baseline — no Triton kernel objects
    # are live in the Triton JIT registry for this import path.
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
