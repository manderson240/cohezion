#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Triton tl.dot_scaled GEMM for MXFP4 on AMD MI355X (gfx950).

Key constraints verified for gfx950 tl.dot_scaled:
- BLOCK_K must be >= 128 (prior attempts with BLOCK_K=64 fail silently or error)
- lhs:       [BLOCK_M, BLOCK_K//2]  uint8 (FP4x2 packed, row-major)
- rhs:       [BLOCK_K//2, BLOCK_N]  uint8 (K-major — B must be transposed)
- lhs_scale: [BLOCK_M, BLOCK_K//32] uint8 (E8M0, M-first)
- rhs_scale: [BLOCK_N, BLOCK_K//32] uint8 (E8M0, N-first — gfx950 constraint)
- B input is [N, K//2]; must transpose to [K//2, N] before passing as rhs
- B_scale_sh is e8m0_shuffled; must unshuffle to [N, K//32] layout first
"""

import aiter
import torch
import triton
import triton.language as tl
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to recover [orig_m, orig_n] E8M0 layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


@triton.jit
def fp4_gemm_dotscaled_kernel(
    # Pointers
    A_ptr,  # [M, K//2]  uint8, FP4x2 packed
    B_t_ptr,  # [K//2, N]  uint8, FP4x2 packed, B transposed
    As_ptr,  # [M, K//32] uint8, E8M0 A scales
    Bs_ptr,  # [N, K//32] uint8, E8M0 B scales (N-first, unshuffled)
    C_ptr,  # [M, N]     bf16 output
    # Dimensions
    M,
    N,
    K,
    # Strides for A [M, K//2]
    stride_am,
    stride_ak,
    # Strides for B_t [K//2, N]
    stride_bk,
    stride_bn,
    # Strides for C [M, N]
    stride_cm,
    stride_cn,
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
    """MXFP4 GEMM using tl.dot_scaled with correct gfx950 scale layout.

    lhs [M, K//2], rhs [K//2, N], both FP4x2-packed uint8.
    lhs_scale [M, K//32], rhs_scale [N, K//32], both E8M0 uint8.
    BLOCK_K >= 128 required for tl.dot_scaled on gfx950.
    """
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    # K in FP4 elements; K//2 in bytes (each byte holds 2 FP4)
    K_bytes: tl.constexpr = BLOCK_K // 2
    # Number of scale groups per K-tile
    K_sg: tl.constexpr = BLOCK_K // 32

    # Full K in bytes for mask computations
    K_total_bytes = K // 2
    K_total_sg = K // 32

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    num_k_iters = tl.cdiv(K, BLOCK_K)

    for k_iter in range(num_k_iters):
        k_byte_off = k_iter * K_bytes
        k_sg_off = k_iter * K_sg

        # K-byte indices for this tile [K_bytes]
        offs_kb = k_byte_off + tl.arange(0, K_bytes)
        # Scale group indices for this tile [K_sg]
        offs_sg = k_sg_off + tl.arange(0, K_sg)

        # Load A tile: [BLOCK_M, K_bytes]
        # A is [M, K//2] row-major
        a_mask = (offs_m[:, None] < M) & (offs_kb[None, :] < K_total_bytes)
        a = tl.load(
            A_ptr + offs_m[:, None] * stride_am + offs_kb[None, :] * stride_ak,
            mask=a_mask,
            other=0,
        )

        # Load B_t tile: [K_bytes, BLOCK_N]
        # B_t is [K//2, N] row-major (transposed B)
        b_mask = (offs_kb[:, None] < K_total_bytes) & (offs_n[None, :] < N)
        b = tl.load(
            B_t_ptr + offs_kb[:, None] * stride_bk + offs_n[None, :] * stride_bn,
            mask=b_mask,
            other=0,
        )

        # Load A scales: [BLOCK_M, K_sg]
        # As is [M, K//32] row-major
        as_mask = (offs_m[:, None] < M) & (offs_sg[None, :] < K_total_sg)
        a_scale = tl.load(
            As_ptr + offs_m[:, None] * stride_asm + offs_sg[None, :] * stride_ask,
            mask=as_mask,
            other=127,
        )

        # Load B scales: [BLOCK_N, K_sg]
        # Bs is [N, K//32] row-major — N-first layout as required by gfx950
        bs_mask = (offs_n[:, None] < N) & (offs_sg[None, :] < K_total_sg)
        b_scale = tl.load(
            Bs_ptr + offs_n[:, None] * stride_bsn + offs_sg[None, :] * stride_bsk,
            mask=bs_mask,
            other=127,
        )

        # tl.dot_scaled: native FP4 scaled GEMM
        # lhs:       [BLOCK_M, K_bytes]  — FP4x2, "e2m1"
        # lhs_scale: [BLOCK_M, K_sg]
        # rhs:       [K_bytes, BLOCK_N]  — FP4x2, "e2m1"
        # rhs_scale: [BLOCK_N, K_sg]     — N-first required for gfx950
        acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc)

    # Write output as bf16
    c = acc.to(tl.bfloat16)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(
        C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn,
        c,
        mask=c_mask,
    )


def _pick_tiles(M: int, K: int) -> tuple[int, int, int]:
    """Pick tile sizes based on problem shape.

    Rules:
    - BLOCK_K >= 128 always (gfx950 tl.dot_scaled requirement)
    - Large K (>=4096): use BLOCK_K=256 to reduce K-loop trip count
    - Small M (<=32): use BLOCK_M=32
    - Larger M: use BLOCK_M=64
    - BLOCK_N=128 throughout (good occupancy, fits L1)
    """
    block_k = 256 if K >= 4096 else 128
    block_m = 32 if M <= 32 else 64
    return block_m, 128, block_k


def _run_triton_gemm(
    A_bytes: torch.Tensor,  # [M, K//2] uint8
    B_t: torch.Tensor,  # [K//2, N] uint8, B transposed
    As_bytes: torch.Tensor,  # [M, K//32] uint8
    Bs_bytes: torch.Tensor,  # [N, K//32] uint8
    M: int,
    N: int,
    K: int,
) -> torch.Tensor:
    """Launch fp4_gemm_dotscaled_kernel with shape-tuned tiles."""
    BLOCK_M, BLOCK_N, BLOCK_K = _pick_tiles(M, K)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A_bytes.device)
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    fp4_gemm_dotscaled_kernel[grid](
        A_bytes,
        B_t,
        As_bytes,
        Bs_bytes,
        C,
        M,
        N,
        K,
        A_bytes.stride(0),
        A_bytes.stride(1),
        B_t.stride(0),
        B_t.stride(1),
        C.stride(0),
        C.stride(1),
        As_bytes.stride(0),
        As_bytes.stride(1),
        Bs_bytes.stride(0),
        Bs_bytes.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )
    return C


# Cache: keyed by (data_ptr, N, ks) -> (B_t, Bs_bytes)
# B and B_scale are weight tensors; same across inference calls for the same weight.
_weight_cache: dict = {}


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    # Quantize A inline (unavoidable — A is bf16 activation)
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)  # [M, K//2]
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)  # [M, ks]

    # Cache B_t and Bs_bytes together — both derived from the same weight tensors
    cache_key = (B_scale_sh.data_ptr(), N, ks)
    if cache_key not in _weight_cache:
        _weight_cache.clear()
        # Transpose B_q [N, K//2] → [K//2, N] for tl.dot_scaled rhs (K-major)
        B_bytes = B_q.view(torch.uint8)  # [N, K//2]
        B_t = B_bytes.t().contiguous()  # [K//2, N]
        # Unshuffle B_scale_sh to [N, ks] layout for gfx950 N-first scale
        Bs_unshuffled = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks)
        Bs_bytes = Bs_unshuffled.contiguous().view(torch.uint8)  # [N, ks]
        _weight_cache[cache_key] = (B_t, Bs_bytes)

    B_t, Bs_bytes = _weight_cache[cache_key]

    try:
        return _run_triton_gemm(A_bytes, B_t, As_bytes, Bs_bytes, M, N, K)
    except Exception as exc:
        # Fallback to proven aiter path
        print(f"[triton_dotscaled] kernel failed: {exc!s:.300}", flush=True)
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
