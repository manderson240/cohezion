"""MLA decode submission — Triton-fused attention kernel.

Uses Triton to fuse attention computation for better performance.

DeepSeek R1 MLA parameters:
- Q dimension: 576 (KV_LORA_RANK 512 + QK_ROPE_HEAD_DIM 64)
- V dimension: 512 (KV_LORA_RANK)
- Loose tolerance: rtol=0.1, atol=0.1
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
PAGE_SIZE = 1


@triton.jit
def mla_decode_fwd_kernel(
    Q,  # [total_q, num_heads, qk_dim]
    KV,  # [total_kv, num_kv_heads, qk_dim]
    Out,  # [total_q, num_heads, v_dim]
    qo_indptr,  # [batch_size + 1]
    kv_indptr,  # [batch_size + 1]
    num_heads: tl.constexpr,
    num_kv_heads: tl.constexpr,
    qk_dim: tl.constexpr,
    v_dim: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    """Fused MLA decode kernel - simplified for compilation.

    Processes queries in parallel. Each block handles:
    - BLOCK_M query tokens
    - All KV positions (loop over KV in tiles)
    - Single head (per block)
    """
    # Program IDs
    pid_m = tl.program_id(0)  # Query block index
    pid_h = tl.program_id(1)  # Head index

    # Get sequence lengths from indptr (bs=1 assumed)
    q_start = tl.load(qo_indptr)
    q_end = tl.load(qo_indptr + 1)
    kv_start = tl.load(kv_indptr)
    kv_end = tl.load(kv_indptr + 1)

    seq_len_q = q_end - q_start
    seq_len_kv = kv_end - kv_start

    # Query indices
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < seq_len_q

    # Initialize accumulators for online softmax
    m_i = tl.full([BLOCK_M], value=-float("inf"), dtype=tl.float32)
    l_i = tl.full([BLOCK_M], value=0.0, dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, v_dim], dtype=tl.float32)

    # Iterate over KV blocks
    num_kv_blocks = tl.cdiv(seq_len_kv, BLOCK_N)

    for kv_block_idx in range(num_kv_blocks):
        offs_n = kv_block_idx * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_n = offs_n < seq_len_kv

        # Compute Q @ K^T for this KV block
        # Q: [BLOCK_M, qk_dim], K: [BLOCK_N, qk_dim]
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        # Tile over head dimension
        for d_start in range(0, qk_dim, 64):
            d_offs = d_start + tl.arange(0, 64)
            d_mask = d_offs < qk_dim

            # Load Q tile: [BLOCK_M, min(64, qk_dim-d_start)]
            q_ptrs = (
                Q
                + (q_start + offs_m[:, None]) * num_heads * qk_dim
                + pid_h * qk_dim
                + d_offs[None, :]
            )
            q_mask = mask_m[:, None] & d_mask[None, :]
            q_tile = tl.load(q_ptrs, mask=q_mask, other=0.0)

            # Load K tile: [BLOCK_N, min(64, qk_dim-d_start)]
            k_ptrs = KV + (kv_start + offs_n[:, None]) * num_kv_heads * qk_dim + d_offs[None, :]
            k_mask = mask_n[:, None] & d_mask[None, :]
            k_tile = tl.load(k_ptrs, mask=k_mask, other=0.0)

            # Accumulate: qk += Q @ K^T
            qk += tl.dot(q_tile, tl.trans(k_tile))

        # Apply softmax scale
        qk *= SM_SCALE

        # Online softmax update
        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        p = tl.exp(qk - m_ij[:, None])
        l_i = l_i * tl.exp(m_i - m_ij) + tl.sum(p, axis=1)
        m_i = m_ij

        # Load V and accumulate weighted sum
        # V is first v_dim elements of KV
        for v_start in range(0, v_dim, 64):
            v_offs = v_start + tl.arange(0, 64)
            v_mask = v_offs < v_dim

            # Load V tile: [BLOCK_N, min(64, v_dim-v_start)]
            v_ptrs = KV + (kv_start + offs_n[:, None]) * num_kv_heads * qk_dim + v_offs[None, :]
            v_mask_full = mask_n[:, None] & v_mask[None, :]
            v_tile = tl.load(v_ptrs, mask=v_mask_full, other=0.0)

            # acc += p @ V (broadcast p over v_dim)
            # p: [BLOCK_M, BLOCK_N], v_tile: [BLOCK_N, v_tile_dim]
            # Need to handle v_tile being smaller than v_dim
            v_tile_t = tl.trans(v_tile)
            p_slice = p[:, :]  # Use full p

            # Simple dot product for this slice
            for m in range(BLOCK_M):
                for n in range(BLOCK_N):
                    if offs_n[n] < seq_len_kv:
                        acc[m, v_start : v_start + 64] += p[m, n] * v_tile[n, :]

    # Normalize
    acc = acc / l_i[:, None]

    # Store output
    out_ptrs = (
        Out
        + (q_start + offs_m[:, None]) * num_heads * v_dim
        + pid_h * v_dim
        + tl.arange(0, v_dim)[None, :]
    )
    out_mask = mask_m[:, None] & (tl.arange(0, v_dim)[None, :] < v_dim)
    tl.store(out_ptrs, acc.to(tl.bfloat16), mask=out_mask)


def custom_kernel(data: input_t) -> output_t:
    """Custom kernel using Triton-fused attention."""
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

    # Kernel config
    BLOCK_M = 32
    BLOCK_N = 32

    # Grid
    num_q_blocks = triton.cdiv(total_q, BLOCK_M)
    grid = (num_q_blocks, NUM_HEADS, bs)

    # Launch
    mla_decode_fwd_kernel[grid](
        q,
        kv_flat,
        output,
        qo_indptr,
        kv_indptr,
        NUM_HEADS,
        NUM_KV_HEADS,
        QK_HEAD_DIM,
        V_HEAD_DIM,
        BLOCK_M,
        BLOCK_N,
    )

    return output
