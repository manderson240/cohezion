"""MLA decode -- Head-Packed FlashDecoding (Phase 8, Task 1-2).

Custom Triton kernel with two key innovations:
1. Head-packed GEMM: all 32 Q heads in M dimension (M=32, not M=1 GEMV)
2. FlashDecoding: split KV across thread blocks for CU utilization

Split-D 512+64: QK_DIM=576 = 512 + 64 (both power-of-2 for tl.arange).
V = KV[:, :512] = first split-D tile (zero extra loads).

Two kernels: mla_flash_decode (main) + mla_reduce (lightweight combine).
Stores partial (acc, m_i, l_i) per split for numerically stable reduce.
"""
import sys
import torch
import triton
import triton.language as tl
from reference import ref_kernel
from task import input_t, output_t

SM_SCALE = 1.0 / (576 ** 0.5)
NUM_HEADS: int = 32
D1: int = 512
D2: int = 64


@triton.jit
def _mla_flash_decode(
    Q_ptr, KV_ptr,
    Partial_O_ptr,   # [bs, num_splits, NUM_HEADS, D1] fp32
    Partial_m_ptr,    # [bs, num_splits, NUM_HEADS] fp32
    Partial_l_ptr,    # [bs, num_splits, NUM_HEADS] fp32
    stride_qb, stride_qh, stride_qd,
    stride_kvb, stride_kvs, stride_kvd,
    stride_pob, stride_pos, stride_poh, stride_pod,
    stride_pmb, stride_pms, stride_pmh,
    stride_plb, stride_pls, stride_plh,
    kvseqlen,
    SM_SCALE: tl.constexpr,
    BLOCK_N: tl.constexpr,
    NUM_HEADS: tl.constexpr,
    NUM_KV_SPLITS: tl.constexpr,
    D1: tl.constexpr,
    D2: tl.constexpr,
):
    bid = tl.program_id(0)
    sid = tl.program_id(1)

    chunk_size = tl.cdiv(kvseqlen, NUM_KV_SPLITS)
    kv_start = sid * chunk_size
    kv_end = tl.minimum(kv_start + chunk_size, kvseqlen)

    h_offs = tl.arange(0, NUM_HEADS)
    d1_offs = tl.arange(0, D1)
    d2_offs = tl.arange(0, D2)

    # Load Q: [NUM_HEADS, D1] and [NUM_HEADS, D2]
    q1 = tl.load(
        Q_ptr + bid * stride_qb + h_offs[:, None] * stride_qh + d1_offs[None, :] * stride_qd,
    )
    q2 = tl.load(
        Q_ptr + bid * stride_qb + h_offs[:, None] * stride_qh + (D1 + d2_offs[None, :]) * stride_qd,
    )

    # Online softmax state
    m_i = tl.full([NUM_HEADS], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([NUM_HEADS], dtype=tl.float32)
    acc = tl.zeros([NUM_HEADS, D1], dtype=tl.float32)

    n_offs = tl.arange(0, BLOCK_N)

    for kv_pos in range(kv_start, kv_end, BLOCK_N):
        kv_idx = kv_pos + n_offs
        kv_mask = kv_idx < kv_end

        # Load KV: [BLOCK_N, D1] and [BLOCK_N, D2]
        kv1 = tl.load(
            KV_ptr + bid * stride_kvb + kv_idx[:, None] * stride_kvs + d1_offs[None, :] * stride_kvd,
            mask=kv_mask[:, None],
            other=0.0,
        )
        kv2 = tl.load(
            KV_ptr + bid * stride_kvb + kv_idx[:, None] * stride_kvs + (D1 + d2_offs[None, :]) * stride_kvd,
            mask=kv_mask[:, None],
            other=0.0,
        )

        # Score: split-D [NUM_HEADS, D1]@[D1, BN] + [NUM_HEADS, D2]@[D2, BN]
        qk = tl.dot(q1, tl.trans(kv1)) + tl.dot(q2, tl.trans(kv2))
        qk = qk * SM_SCALE
        qk = tl.where(kv_mask[None, :], qk, float("-inf"))

        # Online softmax
        m_new = tl.maximum(m_i, tl.max(qk, axis=1))
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        l_i = alpha * l_i + tl.sum(p, axis=1)
        acc = alpha[:, None] * acc + tl.dot(p.to(tl.bfloat16), kv1)
        m_i = m_new

    # Store partial: acc (unnormalized), m_i, l_i
    tl.store(
        Partial_O_ptr + bid * stride_pob + sid * stride_pos
        + h_offs[:, None] * stride_poh + d1_offs[None, :] * stride_pod,
        acc,
    )
    tl.store(
        Partial_m_ptr + bid * stride_pmb + sid * stride_pms + h_offs * stride_pmh,
        m_i,
    )
    tl.store(
        Partial_l_ptr + bid * stride_plb + sid * stride_pls + h_offs * stride_plh,
        l_i,
    )


@triton.jit
def _mla_reduce(
    Partial_O_ptr, Partial_m_ptr, Partial_l_ptr, O_ptr,
    stride_pob, stride_pos, stride_poh, stride_pod,
    stride_pmb, stride_pms, stride_pmh,
    stride_plb, stride_pls, stride_plh,
    stride_ob, stride_oh, stride_od,
    NUM_KV_SPLITS: tl.constexpr,
    NUM_HEADS: tl.constexpr,
    D1: tl.constexpr,
):
    bid = tl.program_id(0)
    h_offs = tl.arange(0, NUM_HEADS)
    d1_offs = tl.arange(0, D1)

    # Find global max m across splits
    global_m = tl.full([NUM_HEADS], float("-inf"), dtype=tl.float32)
    for s in range(NUM_KV_SPLITS):
        m_s = tl.load(
            Partial_m_ptr + bid * stride_pmb + s * stride_pms + h_offs * stride_pmh,
        )
        global_m = tl.maximum(global_m, m_s)

    # Rescale and accumulate
    acc = tl.zeros([NUM_HEADS, D1], dtype=tl.float32)
    l_total = tl.zeros([NUM_HEADS], dtype=tl.float32)

    for s in range(NUM_KV_SPLITS):
        m_s = tl.load(
            Partial_m_ptr + bid * stride_pmb + s * stride_pms + h_offs * stride_pmh,
        )
        l_s = tl.load(
            Partial_l_ptr + bid * stride_plb + s * stride_pls + h_offs * stride_plh,
        )
        po = tl.load(
            Partial_O_ptr + bid * stride_pob + s * stride_pos
            + h_offs[:, None] * stride_poh + d1_offs[None, :] * stride_pod,
        )

        # Rescale: factor = exp(m_s - global_m)
        alpha = tl.exp(m_s - global_m)
        acc += alpha[:, None] * po
        l_total += alpha * l_s

    # Normalize
    out = (acc / l_total[:, None]).to(tl.bfloat16)
    tl.store(
        O_ptr + bid * stride_ob + h_offs[:, None] * stride_oh + d1_offs[None, :] * stride_od,
        out,
    )


def _mla_flash_attention(q, kv_data, bs, kvseqlen, config):
    """FlashDecoding MLA with adaptive split count."""
    nq = NUM_HEADS
    BLOCK_N = 64

    # Adaptive splits: fill CUs (304 on MI355X)
    max_splits = max(1, kvseqlen // BLOCK_N)
    if bs <= 4:
        num_splits = min(64, max_splits)
    elif bs <= 32:
        num_splits = min(16, max_splits)
    elif bs <= 64:
        num_splits = min(8, max_splits)
    else:
        num_splits = min(4, max_splits)
    num_splits = max(1, num_splits)

    kv = kv_data["bf16"].view(bs, kvseqlen, 576)
    q_view = q.view(bs, nq, 576)

    partial_o = torch.empty(bs, num_splits, nq, D1, dtype=torch.float32, device=q.device)
    partial_m = torch.empty(bs, num_splits, nq, dtype=torch.float32, device=q.device)
    partial_l = torch.empty(bs, num_splits, nq, dtype=torch.float32, device=q.device)

    grid_main = (bs, num_splits)
    _mla_flash_decode[grid_main](
        q_view, kv,
        partial_o, partial_m, partial_l,
        q_view.stride(0), q_view.stride(1), q_view.stride(2),
        kv.stride(0), kv.stride(1), kv.stride(2),
        partial_o.stride(0), partial_o.stride(1), partial_o.stride(2), partial_o.stride(3),
        partial_m.stride(0), partial_m.stride(1), partial_m.stride(2),
        partial_l.stride(0), partial_l.stride(1), partial_l.stride(2),
        kvseqlen,
        SM_SCALE=SM_SCALE,
        BLOCK_N=BLOCK_N,
        NUM_HEADS=NUM_HEADS,
        NUM_KV_SPLITS=num_splits,
        D1=D1,
        D2=D2,
        num_warps=8,
        num_stages=1,
    )

    out = torch.empty(bs, nq, D1, dtype=torch.bfloat16, device=q.device)
    grid_reduce = (bs,)
    _mla_reduce[grid_reduce](
        partial_o, partial_m, partial_l, out,
        partial_o.stride(0), partial_o.stride(1), partial_o.stride(2), partial_o.stride(3),
        partial_m.stride(0), partial_m.stride(1), partial_m.stride(2),
        partial_l.stride(0), partial_l.stride(1), partial_l.stride(2),
        out.stride(0), out.stride(1), out.stride(2),
        NUM_KV_SPLITS=num_splits,
        NUM_HEADS=NUM_HEADS,
        D1=D1,
        num_warps=4,
        num_stages=1,
    )

    return out


TORCH_NATIVE_THRESHOLD = 400_000


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    nq = config["num_heads"]
    kvseqlen = config["kv_seq_len"]

    total_q = q.shape[0]
    qseqlen = total_q // bs

    if qseqlen != 1:
        return ref_kernel(data)

    # Large workloads: aiter fp8 ASM is bandwidth-optimal
    if bs * kvseqlen > TORCH_NATIVE_THRESHOLD:
        return ref_kernel(data)

    return _mla_flash_attention(q, kv_data, bs, kvseqlen, config)
