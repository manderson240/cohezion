"""FlyDSL-generated GEMM kernel."""

import triton
import triton.language as tl
from task import input_t, output_t
try:
    from aiter import dtypes
    import aiter
    AITER_AVAILABLE = True
except ImportError:
    AITER_AVAILABLE = False


@triton.jit
def _gemm_kernel(
    A_ptr, A_scale_ptr, B_ptr, B_scale_ptr, C_ptr,
    M, N, K_half,
    stride_am, stride_ak, stride_asm, stride_ask,
    stride_bk, stride_bn, stride_bsn, stride_bsk,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    # Swizzling for XCD locality
    GROUP_SIZE_M: tl.constexpr = 8
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16

    for k_start in range(0, K_half, BLOCK_K):
        k_offs = tl.arange(0, BLOCK_K)

        # Load A tile [BLOCK_M, BLOCK_K]
        a_mask = (offs_m[:, None] < M) & ((k_start + k_offs[None, :]) < K_half)
        a = tl.load(A_ptr + offs_m[:, None] * stride_am + (k_start + k_offs[None, :]) * stride_ak, mask=a_mask, other=0)

        # Load A scale [BLOCK_M, SCALE_PER_BLOCK]
        scale_k_start = k_start // 16
        scale_offs = tl.arange(0, SCALE_PER_BLOCK)
        a_scale = tl.load(A_scale_ptr + offs_m[:, None] * stride_asm + (scale_k_start + scale_offs[None, :]) * stride_ask, mask=(offs_m[:, None] < M), other=0)

        # Load B tile [BLOCK_K, BLOCK_N]
        b_mask = ((k_start + k_offs[:, None]) < K_half) & (offs_n[None, :] < N)
        b = tl.load(B_ptr + (k_start + k_offs[:, None]) * stride_bk + offs_n[None, :] * stride_bn, mask=b_mask, other=0)

        # Load B scale [BLOCK_N, SCALE_PER_BLOCK]
        b_scale = tl.load(B_scale_ptr + offs_n[:, None] * stride_bsn + (scale_k_start + scale_offs[None, :]) * stride_bsk, mask=(offs_n[:, None] < N), other=0)

        # MXFP4 dot product via tl.dot_scaled
        acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)

    # Store result
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn, acc.to(tl.bfloat16), mask=c_mask)


def custom_kernel(data: input_t) -> output_t:
    """FlyDSL gemm kernel."""
    if not AITER_AVAILABLE:
        raise RuntimeError('aiter not available')

    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M, K = A.shape
    N = B.shape[0]

    # Quantize activation to MXFP4
    A_fp4, A_scale = aiter.ops.triton.quant.dynamic_mxfp4_quant(A)
    A_q = A_fp4.view(dtypes.fp4x2)
    A_scale_sh = aiter.utility.fp4_utils.e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)

    # CK GEMM
    C = aiter.gemm_a4w4(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )
    return C