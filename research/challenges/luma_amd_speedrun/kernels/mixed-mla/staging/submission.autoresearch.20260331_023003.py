import torch
import triton
import triton.language as tl
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from aiter.utility.fp4_utils import dynamic_mxfp4_quant, e8m0_to_f32, mxfp4_to_f32
from task import input_t, output_t

# DeepSeek R1 MLA constants
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM ** 0.5)
PAGE_SIZE = 1
NUM_KV_SPLITS = 32

# MXFP4 kernel config
FP4_BLOCK_SIZE = 32


@triton.jit
def _fp4_quantize_kernel(
    X,
    Out,
    Scale,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    offset = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offset < n_elements

    x = tl.load(X + offset, mask=mask).to(tl.float32)
    # Compute block-wise absolute max
    abs_x = tl.abs(x)
    amax = tl.max(abs_x, axis=0)
    # Avoid division by zero
    amax = tl.maximum(amax, 1e-12)
    scale = amax / 15.0  # FP4 max magnitude
    # Quantize to FP4 (4-bit with exponent=0)
    q = tl.clamp(x / scale, -7.5, 7.5)
    # Round to nearest integer
    q = tl.round(q)
    # Pack two FP4 values into one uint8
    q0 = tl.cast(q, tl.int8) & 0xF
    q1 = tl.cast(q + BLOCK_SIZE // 2, tl.int8) & 0xF if (BLOCK_SIZE > 1) else 0
    packed = (q0 | (q1 << 4)).to(tl.uint8)
    tl.store(Out + pid, packed)
    tl.store(Scale + pid, scale)


@triton.jit
def _fp4_gemm_kernel(
    A,  # FP4 packed: uint8
    B,  # FP4 packed: uint8
    C,  # Output: float16
    M,  # rows of A
    N,  # cols of B
    K,  # cols of A / rows of B
    stride_am,
    stride_ak,
    stride_bn,
    stride_bk,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    SPLIT_K: tl.constexpr,
    VECTOR_WIDTH: tl.constexpr,
):
    # Block grid
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    pid_k = tl.program_id(2)

    # Split-K decomposition
    k_per_split = (K + BLOCK_K - 1) // BLOCK_K
    split_k_id = pid_k
    if split_k_id >= k_per_split:
        return

    # Compute base offsets
    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    off_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    off_k = split_k_id * BLOCK_K + tl.arange(0, BLOCK_K)

    # Mask
    m_mask = off_m[:, None] < M
    n_mask = off_n[None, :] < N
    k_mask = off_k[None, :] < K

    # Load A (FP4 packed) and B (FP4 packed)
    A_packed = tl.load(A + off_m[:, None] * stride_am + off_k[None, :] // 2, mask=m_mask & k_mask)
    B_packed = tl.load(B + off_k[:, None] // 2 + off_n[None, :] * stride_bn, mask=k_mask & n_mask)

    # Unpack FP4 to float16
    # Each uint8 holds two FP4 values: lower 4 bits (even), upper 4 bits (odd)
    # A unpacking: [even, odd, even, odd, ...] -> [0,1,2,3,...]
    A_even = (A_packed & 0xF).to(tl.float16)
    A_odd = ((A_packed >> 4) & 0xF).to(tl.float16)
    A_unpack = tl.reshape(
        tl.concatenate([A_even[:, :, None], A_odd[:, :, None]], axis=2),
        (BLOCK_M, BLOCK_K * 2),
    )[:, :BLOCK_K]

    B_even = (B_packed & 0xF).to(tl.float16)
    B_odd = ((B_packed >> 4) & 0xF).to(tl.float16)
    B_unpack = tl.reshape(
        tl.concatenate([B_even[:, :, None], B_odd[:, :, None]], axis=2),
        (BLOCK_K, BLOCK_N * 2),
    )[:BLOCK_K, :]

    # Compute partial sum
    acc = tl.dot(A_unpack, B_unpack, out_dtype=tl.float16)

    # Accumulate across splits
    if SPLIT_K > 1:
        tl.atomic_add(C + off_m[:, None] * stride_cm + off_n[None, :], acc)
    else:
        tl.store(C + off_m[:, None] * stride_cm + off_n[None, :], acc, mask=m_mask & n_mask)


def fp4_gemm(
    A_fp4: torch.Tensor,  # uint8, packed FP4 (shape: [M, K//2])
    B_fp4: torch.Tensor,  # uint8, packed FP4 (shape: [K//2, N])
    scale_A: torch.Tensor,  # float32, [M] or scalar
    scale_B: torch.Tensor,  # float32, [N] or scalar
    M: int,
    N: int,
    K: int,
):
    # Determine block sizes via heuristic sweep (pre-selected for bs=4,kv=1024)
    BLOCK_M, BLOCK_N, BLOCK_K = 64, 64, 64
    SPLIT_K = 2
    VECTOR_WIDTH = 2

    # Launch grid
    grid_m = triton.cdiv(M, BLOCK_M)
    grid_n = triton.cdiv(N, BLOCK_N)
    grid_k = triton.cdiv(K, BLOCK_K)
    grid = (grid_m, grid_n, grid_k * SPLIT_K)

    # Allocate output buffer
    C = torch.zeros((M, N), dtype=torch.float16, device=A_fp4.device)

    # Run kernel
    _fp4_gemm_kernel[grid](
        A_fp4,
        B_fp4,
        C,
        M,
        N,
        K,
        A_fp4.stride(0),
        A_fp4.stride(1),
        B_fp4.stride(0),
        B_fp4.stride(1),
        C.stride(0),
        C.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        SPLIT_K=SPLIT_K,
        VECTOR_WIDTH=VECTOR_WIDTH,
    )

    # Apply scale: C = C * (scale_A * scale_B / 15.0)  [since FP4 max=7.5, quantized range [-7.5,7.5]]
    # But we used scale = amax/15, so dequant = value * scale = value * amax/15
    # Combined scale = scale_A * scale_B / 15.0
    if scale_A.numel() == 1:
        scale_A = scale_A.view(1, 1)
    if scale_B.numel() == 1:
        scale_B = scale_B.view(1, 1)

    scale_total = scale_A * scale_B / 15.0
    C = C * scale_total.to(torch.float16)

    return C


def custom_kernel(data: input_t) -> output_t:
    # Extract inputs
    q_bf16 = data.q  # [total_q, num_heads, 576], bf16
    kv_data = data.kv_data
    kv_bf16 = kv_data.get("bf16")
    kv_fp8_tuple = kv_data.get("fp8")
    kv_mxfp4_tuple = kv_data.get("mxfp4")

    # Fallback to bf16 if no KV provided
    if kv_bf16 is not None:
        kv = kv_bf16
    elif kv_fp8_tuple is not None:
        kv_fp8, kv_scale = kv_fp8_tuple
        kv = kv_fp8.to(torch.bfloat16) * kv_scale
    elif kv_mxfp4_tuple is not None:
        kv_fp4, kv_scale_e8m0 = kv_mxfp4_tuple
        # Dequantize MXFP4 to bf16
        kv = mxfp4_to_f32(kv_fp4, kv_scale_e8m0).to(torch.bfloat16)
    else:
        raise ValueError("No KV data provided")

    # Quantize Q to FP4 (block-32) for fused quant+GEMM path
    total_q, num_heads, _ = q_bf16.shape
    _, num_kv_heads, kv_dim = kv.shape

    # Reshape Q for FP4 quantization (merge heads, align to 32)
    q_flat = q_bf16.reshape(-1, QK_HEAD_DIM)  # [total_q * num_heads, 576]
    # Pad to multiple of FP4_BLOCK_SIZE=32
    pad_q = triton.cdiv(q_flat.shape[0], FP4_BLOCK_SIZE) * FP4_BLOCK_SIZE
    pad_k = triton.cdiv(q_flat.shape[1], FP4_BLOCK_SIZE) * FP4_BLOCK_SIZE
    q_padded = torch.zeros(pad_q, pad_k, dtype=torch.bfloat16, device=q_bf16.device)
    q_padded[: q_flat.shape[0], : q_flat.shape[1]] = q_flat

    # Quantize Q to FP4 (per-block)
    q_fp4_packed = torch.empty(
        (pad_q, pad_k // 2), dtype=torch.uint8, device=q_bf16.device
    )
    q_scale = torch.empty(pad_q // FP4_BLOCK_SIZE, device=q_bf16.device)

    grid = (triton.cdiv(pad_q, FP4_BLOCK_SIZE),)
    _fp4_quantize_kernel[grid](
        q_padded,
        q_fp4_packed,
        q_scale,
        pad_q * pad_k,
        BLOCK_SIZE=FP4_BLOCK_SIZE,
    )
    # Truncate to actual size
    q_fp4_packed = q_fp4_packed[: total_q * num_heads, : kv_dim // 2]
    q_scale = q_scale[: total_q * num_heads]

    # Quantize KV to FP4 (same logic)
    kv_flat = kv.reshape(-1, kv_dim)  # [total_kv * num_kv_heads, 576]
    pad_kv = triton.cdiv(kv_flat.shape[0], FP4_BLOCK_SIZE) * FP4_BLOCK_SIZE
    kv_padded = torch.zeros(pad_kv, pad_k, dtype=torch.bfloat16, device=kv.device)
    kv_padded[: kv_flat.shape[0], : kv_flat.shape[1]] = kv_flat

    kv_fp4_packed = torch.empty(
        (pad_kv, pad_k // 2), dtype=torch.uint8, device=kv.device
    )
    kv_scale = torch.empty(pad_kv // FP4_BLOCK_SIZE, device=kv.device)

    grid = (triton.cdiv(pad_kv, FP4_BLOCK_SIZE),)
    _fp4_quantize_kernel[grid](
        kv_padded,
        kv_fp4_packed,
        kv_scale,
        pad_kv * pad_k,
        BLOCK_SIZE=FP4_BLOCK_SIZE,
    )
    kv_fp4_packed = kv_fp4_packed[: total_q * num_kv_heads, : kv_dim // 2]
    kv_scale = kv_scale[: total_q * num_kv_heads]

    # Reshape for GEMM: [M, K] @ [K, N] -> [M, N]
    M = total_q * num_heads
    N = V_HEAD_DIM
    K = kv_dim

    # Prepare output buffer
    output = torch.empty((M, N), dtype=torch.float16, device=q_bf16.device)

    # FP4 GEMM
    output = fp4_gemm(
        q_fp4_packed,
        kv_fp4_packed.T.contiguous(),
        q_scale,
        kv_scale,
        M,
        N,
        K,
    )

    # Reshape output back to [total_q, num_heads, V_HEAD_DIM]
    output = output.reshape(total_q, num_heads, N)

    # Cast to expected output dtype (bfloat16 for compatibility)
    return output_t(output.to(torch.bfloat16))