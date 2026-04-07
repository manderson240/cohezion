"""
S500 Compliance Probe 2: Triton Dot
Tests if Triton's tl.dot (which uses rocBLAS/SASS) is allowed.
"""
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

import torch
import triton
import triton.language as tl
from task import input_t, output_t

@triton.jit
def simple_dot_kernel(A_ptr, B_ptr, Out_ptr, M, N, K, stride_am, stride_ak, stride_bn, stride_bk, stride_om, stride_on, BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr):
    pid = tl.program_id(0)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    rm = (pid // num_pid_n) * BLOCK_SIZE_M
    rn = (pid % num_pid_n) * BLOCK_SIZE_N
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_SIZE_K):
        a = tl.load(A_ptr + rm * stride_am + k * stride_ak)
        b = tl.load(B_ptr + rn * stride_bn + k * stride_bk)
        acc += tl.dot(a, b)
    tl.store(Out_ptr + rm * stride_om + rn * stride_on, acc.to(torch.bfloat16))

def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]
    out = torch.zeros((m, n), dtype=torch.bfloat16, device=A.device)
    grid = lambda META: (triton.cdiv(m, META['BM']) * triton.cdiv(n, META['BN']), 1, 1)
    simple_dot_kernel[grid](A, B, out, m, n, k, A.stride(0), A.stride(1), B.stride(0), B.stride(1), out.stride(0), out.stride(1), block_M=16, block_N=16, block_K=32)
    return out
