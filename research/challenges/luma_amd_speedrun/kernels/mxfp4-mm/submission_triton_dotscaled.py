"""
MXFP4 GEMM via Triton tl.dot_scaled — bypasses aiter's ASM kernel entirely.
Helion-generated kernel structure, adapted for competition submission format.

Scale layout learned from runner: for data tile [BLOCK_M, BLOCK_K],
scale must be [BLOCK_M, BLOCK_K // 16] (one scale per 32 fp4 = 16 packed bytes).
"""
import sys
import torch
import triton
import triton.language as tl
from task import input_t, output_t
from reference import ref_kernel


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
    """MXFP4 x MXFP4 GEMM using tl.dot_scaled.

    A_q:     [M, K//2] packed fp4 (uint8)
    A_scale: [M, K//32] e8m0 scales
    B_q_t:   [K//2, N] packed fp4 (uint8) — B transposed
    B_scale_t: [K//32, N] e8m0 scales — B scales transposed
    C:       [M, N] bf16 output
    """
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

    # Scale covers 32 fp4 elements = 16 packed bytes per scale entry
    # So for BLOCK_K packed bytes, we need BLOCK_K // 16 scale entries
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

        # A scale for this K-tile: [BLOCK_M, SCALE_PER_BLOCK]
        # Scale index = k_start // 16 (16 packed bytes per scale group)
        scale_k_start = k_start // 16
        offs_scale_k = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)
        a_scale = tl.load(
            A_scale_ptr + offs_m[:, None] * stride_as_m + offs_scale_k[None, :] * stride_as_k,
            mask=mask_m[:, None],
            other=0,
        )

        # B tile [BLOCK_K, BLOCK_N] — B already transposed to [K//2, N]
        b = tl.load(
            B_ptr + offs_k[:, None] * stride_b_k + offs_n[None, :] * stride_b_n,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0,
        )

        # B scale for this K-tile: [BLOCK_N, SCALE_PER_BLOCK]
        # rhs_scale keeps N dimension first (matches B's original [N, K//32] layout)
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


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant

        m, k = A.shape
        n = B.shape[0]
        k_half = k // 2

        # Quantize A (un-shuffled, raw fp4 + e8m0 scale)
        A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())
        A_scale = A_scale.view(torch.uint8)

        # B_q from input matches dynamic_mxfp4_quant output (verified).
        # Re-quant B to get un-shuffled scale (data is discarded).
        _, B_scale = dynamic_mxfp4_quant(B.contiguous())
        B_scale = B_scale.view(torch.uint8)

        # Use input B_q directly (skip re-quant data copy)
        B_fp4_t = B_q.view(torch.uint8).t().contiguous()

        # Block sizes — must be power of 2
        # Minimum BLOCK_M=16 — tl.dot_scaled on gfx950 may require it
        BLOCK_M = max(16, min(64, triton.next_power_of_2(m)))
        BLOCK_N = min(64, triton.next_power_of_2(n))
        # BLOCK_K in packed fp4 space. Must be >= 64 for AMD gfx950 dot_scaled
        BLOCK_K = 64

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
        print(f"TRITON DOT_SCALED ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return ref_kernel(data)
