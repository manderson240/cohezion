"""
MXFP4 GEMM via Triton tl.dot_scaled — bypasses aiter's ASM kernel.

Diagnostic fix for M=64 bug: cap BLOCK_M at 32 to avoid single-tile-M
edge case with BLOCK_M=64. This forces M=64 into 2 tiles.

Falls back to aiter gemm_a4w4 if Triton fails (retains 24.3us baseline).
"""
import sys

import torch
import triton
import triton.language as tl
from task import input_t, output_t


@triton.jit
def _mxfp4_gemm_kernel(
    A_ptr, A_scale_ptr,
    B_ptr, B_scale_ptr,
    C_ptr,
    M, N, K_HALF,
    stride_a_m, stride_a_k,
    stride_as_m, stride_as_k,
    stride_b_k, stride_b_n,
    stride_bs_n, stride_bs_k,
    stride_c_m, stride_c_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    """MXFP4 x MXFP4 GEMM using tl.dot_scaled with 2D grid (no swizzle)."""
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

    # 32 fp4 elements = 16 packed bytes per scale entry
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16

    for k_start in range(0, K_HALF, BLOCK_K):
        offs_k = k_start + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K_HALF

        # A tile [BLOCK_M, BLOCK_K] — packed fp4 data
        a = tl.load(
            A_ptr + offs_m[:, None] * stride_a_m + offs_k[None, :] * stride_a_k,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0,
        )

        # A scale [BLOCK_M, SCALE_PER_BLOCK]
        scale_k_start = k_start // 16
        offs_scale_k = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)
        a_scale = tl.load(
            A_scale_ptr + offs_m[:, None] * stride_as_m + offs_scale_k[None, :] * stride_as_k,
            mask=mask_m[:, None],
            other=0,
        )

        # B tile [BLOCK_K, BLOCK_N] — B transposed to [K//2, N]
        b = tl.load(
            B_ptr + offs_k[:, None] * stride_b_k + offs_n[None, :] * stride_b_n,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0,
        )

        # B scale [BLOCK_N, SCALE_PER_BLOCK] — N-first layout
        b_scale = tl.load(
            B_scale_ptr + offs_n[:, None] * stride_bs_n + offs_scale_k[None, :] * stride_bs_k,
            mask=mask_n[:, None],
            other=0,
        )

        acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)

    c = acc.to(tl.bfloat16)
    tl.store(
        C_ptr + offs_m[:, None] * stride_c_m + offs_n[None, :] * stride_c_n,
        c,
        mask=mask_m[:, None] & mask_n[None, :],
    )


def _aiter_fallback(data: input_t) -> output_t:
    """Fallback to aiter gemm_a4w4 (24.3us baseline)."""
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant

        m, k = A.shape
        n = B.shape[0]
        k_half = k // 2

        # Quantize A (un-shuffled, raw fp4 + e8m0 scale)
        A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())
        A_scale = A_scale[:m, :].contiguous().view(torch.uint8)

        # Re-quant B to get un-shuffled scale
        _, B_scale = dynamic_mxfp4_quant(B.contiguous())
        B_scale = B_scale[:n, :].contiguous().view(torch.uint8)

        # B data transposed to [K//2, N]
        B_fp4_t = B_q.view(torch.uint8).t().contiguous()

        # Cap BLOCK_M at 32 — forces M=64 into 2 tiles (diagnostic for M=64 bug)
        BLOCK_M = max(16, min(32, triton.next_power_of_2(m)))
        BLOCK_N = min(64, triton.next_power_of_2(n))
        BLOCK_K = 64  # minimum for gfx950 dot_scaled

        C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)
        grid = (triton.cdiv(m, BLOCK_M), triton.cdiv(n, BLOCK_N))

        _mxfp4_gemm_kernel[grid](
            A_fp4, A_scale,
            B_fp4_t, B_scale,
            C,
            m, n, k_half,
            A_fp4.stride(0), A_fp4.stride(1),
            A_scale.stride(0), A_scale.stride(1),
            B_fp4_t.stride(0), B_fp4_t.stride(1),
            B_scale.stride(0), B_scale.stride(1),
            C.stride(0), C.stride(1),
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_K=BLOCK_K,
        )
        return C

    except Exception as e:
        print(f"TRITON FALLBACK: {type(e).__name__}: {e}", file=sys.stderr)
        return _aiter_fallback(data)
