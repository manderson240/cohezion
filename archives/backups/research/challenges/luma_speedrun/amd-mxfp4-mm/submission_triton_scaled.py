#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Triton tl.dot_scaled GEMM — native FP4 scaled matmul.

Uses Triton 3.6's tl.dot_scaled which handles MXFP4 block scaling natively.
The hardware MFMA scale instruction is used under the hood.
Falls back to aiter if Triton kernel fails.
"""

import aiter
import torch
import triton
import triton.language as tl
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


@triton.jit
def fp4_gemm_scaled_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    As_ptr,
    Bs_ptr,
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bn,
    stride_bk,
    stride_cm,
    stride_cn,
    stride_asm,
    stride_ask,
    stride_bsn,
    stride_bsk,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    K_BYTES = K // 2  # FP4x2 packing

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        offs_k = k * BLOCK_K + tl.arange(0, BLOCK_K)
        offs_kb = offs_k // 2  # byte offset for fp4x2

        # Load A tile [BLOCK_M, BLOCK_K/2] bytes
        a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_kb[None, :]
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (offs_kb[None, :] < K_BYTES), other=0)

        # Load B tile [BLOCK_N, BLOCK_K/2] bytes (B is N×K/2)
        b_ptrs = B_ptr + offs_n[:, None] * stride_bn + offs_kb[None, :]
        b = tl.load(b_ptrs, mask=(offs_n[:, None] < N) & (offs_kb[None, :] < K_BYTES), other=0)

        # Load A scales [BLOCK_M, BLOCK_K/32]
        offs_sg = k * (BLOCK_K // 32) + tl.arange(0, max(1, BLOCK_K // 32))
        a_scale = tl.load(
            As_ptr + offs_m[:, None] * stride_asm + offs_sg[None, :],
            mask=(offs_m[:, None] < M),
            other=127,
        )
        b_scale = tl.load(
            Bs_ptr + offs_n[:, None] * stride_bsn + offs_sg[None, :],
            mask=(offs_n[:, None] < N),
            other=127,
        )

        # tl.dot_scaled: native FP4 scaled dot product
        # lhs: [BLOCK_M, BLOCK_K/2] uint8, lhs_scale: [BLOCK_M, BLOCK_K/32]
        # rhs: [BLOCK_K/2, BLOCK_N] uint8 (K×N), rhs_scale: [BLOCK_N, BLOCK_K/32]
        # B is stored as [N, K/2] so b is [BLOCK_N, BLOCK_K/2] — need trans
        acc = tl.dot_scaled(a, a_scale, "e2m1", tl.trans(b), b_scale, "e2m1", acc)

    # Store as bf16
    c = acc.to(tl.bfloat16)
    c_ptrs = C_ptr + offs_m[:, None] * stride_cn + offs_n[None, :]
    tl.store(c_ptrs, c, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    # Quantize A
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)

    # B: use raw B_q (not shuffled) for Triton kernel
    B_bytes = B_q.view(torch.uint8)

    # B scale: unshuffle
    def e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
        sm, sn = scale_shuffled.shape
        scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
        scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
        return scale.view(sm, sn)[:orig_m, :orig_n]

    Bs_bytes = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous().view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    try:
        BLOCK_M = min(32, triton.next_power_of_2(M))
        BLOCK_N = 32
        BLOCK_K = 64

        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

        fp4_gemm_scaled_kernel[grid](
            A_bytes,
            B_bytes,
            C,
            As_bytes,
            Bs_bytes,
            M,
            N,
            K,
            A_bytes.stride(0),
            A_bytes.stride(1),
            B_bytes.stride(0),
            B_bytes.stride(1),
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
    except Exception as e:
        err_str = str(e)
        print(f"[triton_scaled] Failed: {err_str[:500]}")
        # Fallback to aiter
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
