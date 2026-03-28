"""MLA decode submission — CDNA 4 optimized Triton kernel.

MI355X CDNA 4 optimizations:
- BLOCK_M=64 (MFMA output tile width)
- BLOCK_N=32 (KV processing granularity)
- BLOCK_K=64 (MFMA accumulation dimension)
- Online softmax in registers
- Single kernel launch

DeepSeek R1 MLA:
- QK_HEAD_DIM: 576 (512 + 64)
- V_HEAD_DIM: 512
- SM_SCALE: 1/sqrt(576)
- Tolerance: rtol=0.1, atol=0.1
"""

import torch
import triton
import triton.language as tl
from task import input_t, output_t


# ── DeepSeek R1 MLA constants ──
NUM_HEADS = 16
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)


@triton.jit
def mla_decode_fwd_kernel(
    Q,  # [total_q, NUM_HEADS, QK_HEAD_DIM]
    KV,  # [total_kv, NUM_KV_HEADS, QK_HEAD_DIM]
    Out,  # [total_q, NUM_HEADS, V_HEAD_DIM]
    qo_indptr,  # [batch_size + 1]
    kv_indptr,  # [batch_size + 1]
    NUM_HEADS: tl.constexpr,
    NUM_KV_HEADS: tl.constexpr,
    QK_HEAD_DIM: tl.constexpr,
    V_HEAD_DIM: tl.constexpr,
    SM_SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr = 64,
    BLOCK_N: tl.constexpr = 32,
    BLOCK_K: tl.constexpr = 64,
):
    """Fused MLA decode with online softmax.

    Grid: (num_q_blocks, NUM_HEADS, batch_size)
    """
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)

    # Load batch boundaries
    q_start = tl.load(qo_indptr)
    q_end = tl.load(qo_indptr + 1)
    kv_start = tl.load(kv_indptr)
    kv_end = tl.load(kv_indptr + 1)

    seq_q = q_end - q_start
    seq_kv = kv_end - kv_start

    # Query offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < seq_q

    # Online softmax accumulators
    m_i = tl.full([BLOCK_M], value=-float("inf"), dtype=tl.float32)
    l_i = tl.full([BLOCK_M], value=0.0, dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, V_HEAD_DIM], dtype=tl.float32)

    # Process KV blocks
    num_kv_blocks = tl.cdiv(seq_kv, BLOCK_N)

    for kv_block in range(0, num_kv_blocks):
        offs_n = kv_block * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_n = offs_n < seq_kv

        # Compute attention scores: Q @ K^T
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        # Tile over QK_HEAD_DIM
        for k_iter in range(tl.cdiv(QK_HEAD_DIM, BLOCK_K)):
            offs_k = k_iter * BLOCK_K + tl.arange(0, BLOCK_K)
            mask_k = offs_k < QK_HEAD_DIM

            # Load Q: [BLOCK_M, BLOCK_K]
            q_base = (q_start + offs_m[:, None]) * NUM_HEADS * QK_HEAD_DIM + pid_h * QK_HEAD_DIM
            q_ptrs = Q + q_base + offs_k[None, :]
            q_tile = tl.load(q_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)

            # Load K: [BLOCK_N, BLOCK_K] from KV
            k_base = (kv_start + offs_n[:, None]) * NUM_KV_HEADS * QK_HEAD_DIM
            k_ptrs = KV + k_base + offs_k[None, :]
            k_tile = tl.load(k_ptrs, mask=mask_n[:, None] & mask_k[None, :], other=0.0)

            # Matmul with TF32 precision for MFMA
            qk += tl.dot(q_tile, tl.trans(k_tile), input_precision="tf32")

        # Scale
        qk *= SM_SCALE

        # Online softmax
        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        p = tl.exp(qk - m_ij[:, None])
        l_i = l_i * tl.exp(m_i - m_ij) + tl.sum(p, axis=1)
        m_i = m_ij

        # Attention: p @ V, where V is first V_HEAD_DIM of KV
        # V: [seq_kv, V_HEAD_DIM]
        for v_iter in range(tl.cdiv(V_HEAD_DIM, BLOCK_K)):
            offs_v = v_iter * BLOCK_K + tl.arange(0, BLOCK_K)
            mask_v = offs_v < V_HEAD_DIM

            # Load V: [BLOCK_N, BLOCK_K]
            v_base = (kv_start + offs_n[:, None]) * NUM_KV_HEADS * QK_HEAD_DIM
            v_ptrs = KV + v_base + offs_v[None, :]
            v_tile = tl.load(v_ptrs, mask=mask_n[:, None] & mask_v[None, :], other=0.0)

            # acc += p @ V_tile, accumulate into acc
            acc_slice = tl.dot(p, v_tile, out_dtype=tl.float32)

            # Update accumulator at correct offsets
            for i in tl.static_range(0, BLOCK_M):
                for j in tl.static_range(0, BLOCK_K):
                    if offs_v[j] < V_HEAD_DIM:
                        acc[i, offs_v[j]] += acc_slice[i, j]

    # Normalize and store
    acc = acc / l_i[:, None]

    # Store output tiles
    for v_iter in range(tl.cdiv(V_HEAD_DIM, BLOCK_K)):
        offs_v = v_iter * BLOCK_K + tl.arange(0, BLOCK_K)
        mask_v = offs_v < V_HEAD_DIM

        out_base = (offs_m[:, None]) * NUM_HEADS * V_HEAD_DIM + pid_h * V_HEAD_DIM
        out_ptrs = Out + out_base + offs_v[None, :]

        # Gather accumulator values
        out_vals = tl.zeros([BLOCK_M, BLOCK_K], dtype=tl.bfloat16)
        for i in tl.static_range(0, BLOCK_M):
            for j in tl.static_range(0, BLOCK_K):
                if offs_v[j] < V_HEAD_DIM:
                    out_vals[i, j] = tl.cast(acc[i, offs_v[j]], tl.bfloat16)

        tl.store(out_ptrs, out_vals, mask=mask_m[:, None] & mask_v[None, :])


def custom_kernel(data: input_t) -> output_t:
    """CDNA 4 optimized MLA decode."""
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_q = bs * qseqlen
    total_kv = bs * kvseqlen

    # Use bf16 KV
    kv_bf16 = kv_data["bf16"]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

    # Allocate output
    output = torch.empty((total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    # CDNA 4 grid
    BLOCK_M = 64
    num_q_blocks = triton.cdiv(total_q, BLOCK_M)
    grid = (num_q_blocks, NUM_HEADS, bs)

    # Launch kernel
    mla_decode_fwd_kernel[grid](
        q,
        kv_flat,
        output,
        qo_indptr,
        kv_indptr,
        NUM_HEADS=NUM_HEADS,
        NUM_KV_HEADS=NUM_KV_HEADS,
        QK_HEAD_DIM=QK_HEAD_DIM,
        V_HEAD_DIM=V_HEAD_DIM,
        SM_SCALE=SM_SCALE,
        BLOCK_M=BLOCK_M,
        BLOCK_N=32,
        BLOCK_K=64,
    )

    return output
