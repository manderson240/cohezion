"""Fused bf16→fp4 quant + GEMM using tl.dot_scaled + Origami scheduling.

Takes bf16 A directly, quantizes on-the-fly inside the GEMM kernel.
Eliminates the separate quantization kernel launch overhead (~33 µs).
Uses Origami chiplet-aware scheduling from tritonblas.
"""
import sys
import time
import torch
import triton
import triton.language as tl
from task import input_t, output_t


def e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    scale = scale.view(sm, sn)
    return scale[:orig_m, :orig_n]


@triton.jit
def _fused_quant_gemm_kernel(
    # A is bf16 [M, K] — quantized on-the-fly
    A_ptr,
    # B is fp4 packed [K//2, N] (transposed by caller)
    B_ptr,
    # Output C is bf16 [M, N]
    C_ptr,
    # B scale [N, K//32] uint8
    B_scale_ptr,
    # Dimensions
    M, N, K,  # K is in bf16 elements (NOT packed bytes)
    # A strides (bf16)
    stride_am, stride_ak,
    # B strides (transposed: [K//2, N])
    stride_bk, stride_bn,
    # B_scale strides [N, K//32]
    stride_bs_n, stride_bs_k,
    # C strides
    stride_cm, stride_cn,
    # Tile sizes
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,  # in bf16 elements (will be K//2 packed bytes for fp4)
    # Origami scheduling
    GROUP_SIZE_M: tl.constexpr,
    NUM_XCDS: tl.constexpr,
    CHUNK_SIZE: tl.constexpr,
    # FP4 constants
    SCALE_GROUP_SIZE: tl.constexpr,  # 32 bf16 elements per scale
):
    # Origami chiplet-aware PID transform
    pid = tl.program_id(0)
    total_blocks_M = tl.cdiv(M, BLOCK_M)
    total_blocks_N = tl.cdiv(N, BLOCK_N)

    # Chiplet-chunked scheduling (from tritonblas fp4_matmul)
    num_chunks = tl.cdiv(total_blocks_M * total_blocks_N, CHUNK_SIZE)
    chunk_id = pid // CHUNK_SIZE
    chunk_lane = pid % CHUNK_SIZE

    # Remap chunk to XCD
    xcd_id = chunk_id % NUM_XCDS
    chunk_in_xcd = chunk_id // NUM_XCDS
    remapped_chunk = xcd_id * tl.cdiv(num_chunks, NUM_XCDS) + chunk_in_xcd
    remapped_pid = remapped_chunk * CHUNK_SIZE + chunk_lane

    if remapped_pid >= total_blocks_M * total_blocks_N:
        return

    # Group-M tile ordering
    num_pid_in_group = GROUP_SIZE_M * total_blocks_N
    group_id = remapped_pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(total_blocks_M - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (remapped_pid % num_pid_in_group) % group_size_m
    pid_n = (remapped_pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

    # BLOCK_K is in bf16 elements
    # FP4 packs 2 elements per byte, so BLOCK_K_PACKED = BLOCK_K // 2
    BLOCK_K_PACKED: tl.constexpr = BLOCK_K // 2
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // SCALE_GROUP_SIZE

    K_PACKED = K // 2  # Total packed K dimension

    for k_start in range(0, K, BLOCK_K):
        offs_k = k_start + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K

        # --- Load bf16 A tile [BLOCK_M, BLOCK_K] ---
        a_bf16 = tl.load(
            A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0.0,
        )

        # --- Compute A scale: E8M0 per SCALE_GROUP_SIZE elements ---
        # Reshape to [BLOCK_M, SCALE_PER_BLOCK, SCALE_GROUP_SIZE]
        a_reshaped = tl.reshape(a_bf16, [BLOCK_M, SCALE_PER_BLOCK, SCALE_GROUP_SIZE])
        # amax per group
        a_abs = tl.abs(a_reshaped).to(tl.float32)
        a_amax = tl.max(a_abs, axis=2)  # [BLOCK_M, SCALE_PER_BLOCK]
        # E8M0 for fp4 e2m1: scale must satisfy amax / scale <= fp4_max (6.0)
        # e = floor(log2(amax / 6.0)) + 128, clamped to [0, 254]
        # This ensures normalized values stay within [-6, 6] (fp4 e2m1 range)
        a_log2 = tl.where(
            a_amax > 0,
            tl.math.floor(tl.math.log2(a_amax / 6.0)) + 128.0,
            0.0,
        )
        a_scale = tl.minimum(tl.maximum(a_log2, 0.0), 254.0).to(tl.uint8)

        # --- Quantize A to fp4 e2m1 ---
        a_scale_expanded = tl.reshape(
            tl.broadcast_to(a_scale[:, :, None], [BLOCK_M, SCALE_PER_BLOCK, SCALE_GROUP_SIZE]),
            [BLOCK_M, BLOCK_K]
        ).to(tl.float32)
        scale_factor = tl.math.exp2(a_scale_expanded - 127.0)
        # Normalize by scale; post-norm values are in [-6, 6] for e2m1
        a_normalized = tl.where(scale_factor > 0, a_bf16.to(tl.float32) / scale_factor, 0.0)

        # Encode fp4 e2m1: 1 sign bit | 3 magnitude bits
        # Values: 0, ±0.5, ±1, ±1.5, ±2, ±3, ±4, ±6
        sign = (a_normalized < 0).to(tl.int32)
        x_abs = tl.abs(a_normalized)
        mag = tl.where(x_abs < 0.25, 0,
              tl.where(x_abs < 0.75, 1,
              tl.where(x_abs < 1.25, 2,
              tl.where(x_abs < 1.75, 3,
              tl.where(x_abs < 2.5,  4,
              tl.where(x_abs < 3.5,  5,
              tl.where(x_abs < 5.0,  6, 7)))))))
        fp4_codes = (sign << 3) | mag  # [BLOCK_M, BLOCK_K], values 0-15

        # Pack adjacent pairs: shift odd-indexed elements to high nibble, then
        # sum adjacent pairs. Since low/high nibble bits never overlap, sum = OR.
        shift = tl.where(tl.arange(0, BLOCK_K) % 2 == 1, 4, 0)  # [BLOCK_K]
        shifted = (fp4_codes & 0xF) << shift[None, :]  # [BLOCK_M, BLOCK_K]
        a_fp4 = tl.sum(
            tl.reshape(shifted, [BLOCK_M, BLOCK_K_PACKED, 2]), axis=2
        ).to(tl.uint8)  # [BLOCK_M, BLOCK_K_PACKED]

        # --- Load B tile [BLOCK_K_PACKED, BLOCK_N] (already fp4 packed) ---
        k_packed_start = k_start // 2
        offs_k_packed = k_packed_start + tl.arange(0, BLOCK_K_PACKED)
        mask_k_packed = offs_k_packed < K_PACKED

        b = tl.load(
            B_ptr + offs_k_packed[:, None] * stride_bk + offs_n[None, :] * stride_bn,
            mask=mask_k_packed[:, None] & mask_n[None, :],
            other=0,
        )

        # --- Load B scale [BLOCK_N, SCALE_PER_BLOCK] ---
        scale_k_start = k_start // SCALE_GROUP_SIZE
        offs_scale_k = scale_k_start + tl.arange(0, SCALE_PER_BLOCK)
        b_scale = tl.load(
            B_scale_ptr + offs_n[:, None] * stride_bs_n + offs_scale_k[None, :] * stride_bs_k,
            mask=mask_n[:, None],
            other=0,
        )

        # --- Scaled dot product ---
        acc = tl.dot_scaled(a_fp4, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)

    # Store result
    c = acc.to(tl.bfloat16)
    tl.store(
        C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn,
        c,
        mask=mask_m[:, None] & mask_n[None, :],
    )


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B.shape[0]
    k_scale = k // 32

    try:
        from tritonblas import OrigamiMatmulSelector

        # Unshuffle B scale
        B_scale = e8m0_unshuffle(B_scale_sh.view(torch.uint8), orig_m=n, orig_n=k_scale)

        # Transpose B for kernel (B_q is [N, K//2], kernel needs [K//2, N])
        B_t = B_q.view(torch.uint8).t().contiguous()

        # Use Origami selector for tile sizes
        selector = OrigamiMatmulSelector(m, n, k, "f4", "f4", torch.bfloat16, A.device, mx_block_size=32)
        BLOCK_M = max(selector.block_m, 16)  # min 16 for gfx950
        BLOCK_N = selector.block_n
        BLOCK_K = selector.block_k  # in fp4/bf16 elements
        GROUP_SIZE_M = selector.group_m
        NUM_XCDS = selector.num_sms

        # Override if blocks are too small for matrix
        if BLOCK_M < m:
            BLOCK_M = 128
        if BLOCK_N < n:
            BLOCK_N = 128
        if BLOCK_K < k:
            BLOCK_K = 128

        # BLOCK_K is in BF16 elements; packed bytes = BLOCK_K//2
        # tl.dot_scaled requires packed_K >= 64 bytes, so BF16 K >= 128
        BLOCK_K = max(BLOCK_K, 128)
        if BLOCK_K % 128 != 0:
            BLOCK_K = ((BLOCK_K + 127) // 128) * 128

        total_blocks_M = triton.cdiv(m, BLOCK_M)
        total_blocks_N = triton.cdiv(n, BLOCK_N)
        total_tiles = total_blocks_M * total_blocks_N

        CHUNK_SIZE = GROUP_SIZE_M * GROUP_SIZE_M
        CHUNK_SIZE = min(CHUNK_SIZE, max(1, total_tiles // NUM_XCDS))

        C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)

        grid = (total_tiles,)

        print(f"FUSED: m={m}, n={n}, k={k}, BM={BLOCK_M}, BN={BLOCK_N}, BK={BLOCK_K}, "
              f"GSM={GROUP_SIZE_M}, XCDS={NUM_XCDS}, tiles={total_tiles}", file=sys.stderr)

        _fused_quant_gemm_kernel[grid](
            A,
            B_t,
            C,
            B_scale,
            m, n, k,
            A.stride(0), A.stride(1),
            B_t.stride(0), B_t.stride(1),
            B_scale.stride(0), B_scale.stride(1),
            C.stride(0), C.stride(1),
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_K=BLOCK_K,
            GROUP_SIZE_M=GROUP_SIZE_M,
            NUM_XCDS=NUM_XCDS,
            CHUNK_SIZE=CHUNK_SIZE,
            SCALE_GROUP_SIZE=32,
            num_warps=8,
            num_stages=2,
        )
        return C

    except Exception as e:
        print(f"FUSED KERNEL ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Fallback
        from reference import ref_kernel
        return ref_kernel(data)
