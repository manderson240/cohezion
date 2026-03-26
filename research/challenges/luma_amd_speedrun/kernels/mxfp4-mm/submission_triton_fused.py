"""
Custom Triton GEMM kernel with inline MXFP4 quantization.

Fuses: bf16→fp4 quantization + GEMM into single kernel launch.
"""

from __future__ import annotations

import torch
import triton
import triton.language as tl
from task import input_t, output_t


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 16, "BLOCK_N": 256, "BLOCK_K": 128}, num_warps=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 128, "BLOCK_K": 128}, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 128}, num_warps=4),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def fused_gemm_kernel(
    A_ptr,
    B_shuffle_ptr,
    C_ptr,
    A_scale_out_ptr,
    B_scale_ptr,
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bsk,
    stride_bpn,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    num_warps: tl.constexpr,
    GROUP_M: tl.constexpr = 8,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = num_pid_m * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * num_pid_m
    group_size_m = tl.minimum(num_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    rm = tl.arange(0, BLOCK_M)
    rn = tl.arange(0, BLOCK_N)
    rk = tl.arange(0, BLOCK_K)

    A_off = pid_m * BLOCK_M * stride_am + rk
    a = tl.load(A_ptr + A_off, mask=(pid_m * BLOCK_M + rm) < M, other=0.0)
    a = tl.reshape(a, [BLOCK_M, BLOCK_K])

    SCALE_PER_BLOCK = BLOCK_K // 32
    a_reshaped = tl.reshape(a, [BLOCK_M, SCALE_PER_BLOCK, 32])
    a_amax = tl.max(tl.abs(a_reshaped).to(tl.float32), axis=2)

    log_arg = a_amax / 6.0
    log_arg = tl.where(log_arg <= 0, 1.0, log_arg)
    a_log2_pos = tl.floor(tl.math.log2(log_arg)) + 128.0
    a_log2 = tl.where(a_amax > 0, a_log2_pos, 0.0)
    a_scale = tl.minimum(tl.maximum(a_log2, 0.0), 254.0).to(tl.uint8)

    a_scale_expanded = tl.reshape(
        tl.broadcast_to(a_scale[:, :, None], [BLOCK_M, SCALE_PER_BLOCK, 32]), [BLOCK_M, BLOCK_K]
    ).to(tl.float32)
    scale_factor = tl.math.exp2(a_scale_expanded - 127.0)
    a_normalized = tl.where(scale_factor > 0, a.to(tl.float32) / scale_factor, 0.0)

    sign = (a_normalized < 0).to(tl.int32)
    x_abs = tl.abs(a_normalized)

    c0 = x_abs < 0.25
    c1 = x_abs < 0.75
    c2 = x_abs < 1.25
    c3 = x_abs < 1.75
    c4 = x_abs < 2.5
    c5 = x_abs < 3.5
    c6 = x_abs < 5.0

    mag = c0 * 0 + c1 * 1 + c2 * 2 + c3 * 3 + c4 * 4 + c5 * 5 + c6 * 6 + (~c6) * 7
    fp4_codes = (sign << 3) | mag

    BLOCK_K_PACKED = BLOCK_K // 2
    shift = tl.where(rk % 2 == 1, 4, 0)
    shifted = (fp4_codes & 0xF) << shift
    a_fp4 = tl.sum(tl.reshape(shifted, [BLOCK_M, BLOCK_K_PACKED, 2]), axis=2).to(tl.uint8)

    BN_MASK = (rk[:, None] < K) & (rn[None, :] < N)
    B_off = rk[:, None] * stride_bsk + pid_n * BLOCK_N * stride_bpn + rn[None, :]
    b = tl.load(B_shuffle_ptr + B_off, mask=BN_MASK, other=0.0)

    BN_SCALE = N // 32
    b_scale_off = pid_n * BLOCK_N * BN_SCALE + rn[:, None] * (BN_SCALE // 32)
    b_scale_mask = rn[:, None] < N
    b_scale = tl.load(B_scale_ptr + b_scale_off, mask=b_scale_mask, other=0.0).to(tl.uint8)

    acc = tl.dot_scaled(a_fp4, a_scale, "e2m1", b, b_scale, "e2m1")

    C_off = pid_m * BLOCK_M * stride_cm + pid_n * BLOCK_N * stride_cn
    tl.store(C_ptr + C_off + rm[:, None] * stride_cm + rn[None, :] * stride_cn, acc.to(tl.float32))


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    M, K = A.shape
    N = B.shape[1]

    C = torch.zeros(M, N, dtype=torch.float32, device=A.device)

    grid = (M * N,)

    fused_gemm_kernel[grid](
        A,
        B_shuffle,
        C,
        None,
        B_scale_sh,
        M,
        N,
        K,
        A.stride(0),
        A.stride(1),
        B_shuffle.stride(0),
        B_shuffle.stride(1),
        C.stride(0),
        C.stride(1),
    )

    return C.to(torch.bfloat16)
