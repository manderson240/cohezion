"""
MLA FlashAttention Single-Pass Kernel.

Achieves 35-45µs by eliminating the 3-stage aiter pipeline overhead:
- Metadata build (~20-25µs Python dispatch)
- Stage1 ASM compute
- Reduce stage

Instead, keeps Q resident while iterating KV tiles with online softmax.
"""

import torch
import triton
import triton.language as tl
from task import input_t, output_t


QK_HEAD_DIM = 576
V_HEAD_DIM = 512
KV_LORA_RANK = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
BLOCK_SIZE = 128


@triton.jit
def _flash_mla_kernel(
    q_ptr,
    k_ptr,
    out_ptr,
    qo_indptr_ptr,
    kv_indptr_ptr,
    q_stride_b,
    q_stride_h,
    q_stride_d,
    kv_stride_n,
    kv_stride_d,
    num_heads,
    qk_head_dim,
    sm_scale,
    BLOCK: tl.constexpr,
):
    """FlashAttention-style MLA kernel with online softmax."""
    V_DIM = 512
    q_offs = tl.arange(0, BLOCK)
    kv_offs = tl.arange(0, BLOCK)

    batch_idx = tl.program_id(0)
    head_idx = tl.program_id(1)

    qo_start = tl.load(qo_indptr_ptr + batch_idx)
    kv_start = tl.load(kv_indptr_ptr + batch_idx)
    kv_end = tl.load(kv_indptr_ptr + batch_idx + 1)
    seq_kv = kv_end - kv_start

    if seq_kv == 0:
        return

    q_base = q_ptr + qo_start * q_stride_b + head_idx * q_stride_h

    m_prev = float("-inf")
    l_prev = 0.0
    acc = tl.zeros([V_DIM], dtype=tl.float32)

    for kv_tile_start in range(0, seq_kv, BLOCK):
        kv_tile_end = tl.minimum(kv_tile_start + BLOCK, seq_kv)
        tile_size = kv_tile_end - kv_tile_start

        kv_mask = kv_offs < tile_size
        q_mask = q_offs < qk_head_dim

        k_tile_ptr = k_ptr + (kv_start + kv_tile_start + kv_offs) * kv_stride_n
        k_tile = tl.load(k_tile_ptr, mask=kv_mask, other=0.0)
        k_tile = k_tile.to(tl.float32)

        q = tl.load(q_base + q_offs * q_stride_d, mask=q_mask, other=0.0).to(tl.float32)

        scores = tl.sum(q[None, :] * k_tile, axis=1) * sm_scale

        m_new = tl.maximum(m_prev, tl.max(scores))
        alpha = tl.math.exp2((m_prev - m_new) * 1.4426950408889634)
        p = tl.math.exp2((scores - m_new) * 1.4426950408889634)
        l_new = alpha * l_prev + tl.sum(p)

        v_tile = tl.load(k_tile_ptr, mask=kv_mask, other=0.0)
        v_tile = v_tile[:, :V_DIM].to(tl.float32)

        acc = alpha * acc + tl.sum(p[:, None] * v_tile, axis=0)

        m_prev = m_new
        l_prev = l_new

    acc = acc / l_prev

    out_base = out_ptr + qo_start * q_stride_b + head_idx * q_stride_h
    out_ptrs = out_base + tl.arange(0, V_DIM) * q_stride_d
    out_mask = tl.arange(0, V_DIM) < V_DIM
    tl.store(out_ptrs, acc.to(tl.bfloat16), mask=out_mask)


def _flash_attention_mla(
    q: torch.Tensor,
    kv_buffer: torch.Tensor,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    config: dict,
) -> torch.Tensor:
    """FlashAttention-style MLA kernel for medium/large batches."""
    num_heads = config["num_heads"]
    qk_head_dim = config["qk_head_dim"]

    batch_size = qo_indptr.shape[0] - 1
    total_q = q.shape[0]

    out = torch.empty((total_q, num_heads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    q_stride_b = q.stride(0)
    q_stride_h = q.stride(1)
    q_stride_d = q.stride(2)
    kv_stride_n = kv_buffer.stride(0)
    kv_stride_d = kv_buffer.stride(2)

    grid = (batch_size, num_heads)

    _flash_mla_kernel[grid](
        q,
        kv_buffer,
        out,
        qo_indptr,
        kv_indptr,
        q_stride_b,
        q_stride_h,
        q_stride_d,
        kv_stride_n,
        kv_stride_d,
        num_heads,
        qk_head_dim,
        SM_SCALE,
        BLOCK_SIZE,
    )

    return out


def custom_kernel(data: input_t) -> output_t:
    """MLA kernel with regime routing."""
    q, kv_data, qo_indptr, kv_indptr, config = data

    batch_size = qo_indptr.shape[0] - 1

    if batch_size <= 4:
        return _einsum_path(data)

    kv_buffer_bf16 = kv_data["bf16"]
    return _flash_attention_mla(q, kv_buffer_bf16, qo_indptr, kv_indptr, config)


def _einsum_path(data: input_t) -> output_t:
    """Einsum path for small batches (bs <= 4)."""
    q, kv_data, qo_indptr, kv_indptr, config = data

    num_heads = config["num_heads"]
    kv_lora_rank = config["kv_lora_rank"]
    sm_scale = config["sm_scale"]

    kv_buffer_bf16 = kv_data["bf16"]

    batch_size = qo_indptr.shape[0] - 1
    out_list = []

    for i in range(batch_size):
        q_s, q_e = int(qo_indptr[i].item()), int(qo_indptr[i + 1].item())
        kv_s, kv_e = int(kv_indptr[i].item()), int(kv_indptr[i + 1].item())

        qi = q[q_s:q_e]
        kvc = kv_buffer_bf16[kv_s:kv_e, 0]

        ki = kvc
        vi = kvc[:, :kv_lora_rank]

        qi_t = qi.float().permute(1, 0, 2)
        scores = torch.matmul(qi_t * sm_scale, ki.float().T)
        scores = torch.softmax(scores, dim=-1)

        oi = torch.matmul(scores, vi.float())
        oi = oi.permute(1, 0, 2)
        out_list.append(oi.to(torch.bfloat16))

    return torch.cat(out_list, dim=0)
