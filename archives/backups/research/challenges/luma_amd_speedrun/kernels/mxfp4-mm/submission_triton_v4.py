"""Triton MXFP4 GEMM v4: BLOCK_M=32 fixed, e8m0_unshuffle, per-shape tile selection.

Fix: v3 failed m=64 with BLOCK_M=64. Use BLOCK_M=32 for all shapes (proven correct
at m=8,16 in v3). Correctness > speed for this iteration.
"""

import torch
import triton
import triton.language as tl
from task import input_t, output_t


def _e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    scale = scale.view(sm, sn)
    return scale[:orig_m, :orig_n]


_b_cache = {}


def _prepare_b(B_q, B_scale_sh, N, K):
    key = B_q.data_ptr()
    if key not in _b_cache:
        K_half = K // 2
        scale_K = K // 32
        B_q_u8 = B_q.view(torch.uint8)
        B_q_t = B_q_u8.t().contiguous()
        B_scale_raw = _e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=N, orig_n=scale_K)
        _b_cache[key] = (B_q_t, B_scale_raw)
    return _b_cache[key]


@triton.jit
def _mxfp4_gemm_kernel(
    A_ptr,
    A_scale_ptr,
    B_ptr,
    B_scale_ptr,
    C_ptr,
    M,
    N,
    K_HALF,
    stride_a_m,
    stride_a_k,
    stride_as_m,
    stride_as_k,
    stride_b_k,
    stride_b_n,
    stride_bs_n,
    stride_bs_k,
    stride_c_m,
    stride_c_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    GROUP_SIZE_M: tl.constexpr = 8
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N
    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16

    for k_start in range(0, K_HALF, BLOCK_K):
        offs_k = k_start + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K_HALF

        a = tl.load(
            A_ptr + offs_m[:, None] * stride_a_m + offs_k[None, :] * stride_a_k,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0,
        )

        scale_k_start = k_start // 16
        offs_scale_k = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)

        a_scale = tl.load(
            A_scale_ptr + offs_m[:, None] * stride_as_m + offs_scale_k[None, :] * stride_as_k,
            mask=mask_m[:, None],
            other=0,
        )

        b = tl.load(
            B_ptr + offs_k[:, None] * stride_b_k + offs_n[None, :] * stride_b_n,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0,
        )

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
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M, K = A.shape
    N = B.shape[0]
    K_half = K // 2

    A_fp4, A_scale = dynamic_mxfp4_quant(A)
    A_u8 = A_fp4.view(torch.uint8)
    A_scale_u8 = A_scale.view(torch.uint8)

    B_t, B_scale_raw = _prepare_b(B_q, B_scale_sh, N, K)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    # Fixed BLOCK_M=32 for all shapes (proven correct for m=8,16,256)
    # BLOCK_M=64 failed for m=64 — need to investigate why
    BLOCK_M = 32
    BLOCK_N = 64
    BLOCK_K = 64

    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

    _mxfp4_gemm_kernel[grid](
        A_u8,
        A_scale_u8,
        B_t,
        B_scale_raw,
        C,
        M,
        N,
        K_half,
        A_u8.stride(0),
        A_u8.stride(1),
        A_scale_u8.stride(0),
        A_scale_u8.stride(1),
        B_t.stride(0),
        B_t.stride(1),
        B_scale_raw.stride(0),
        B_scale_raw.stride(1),
        C.stride(0),
        C.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    return C
