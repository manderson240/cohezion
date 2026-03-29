"""MLA decode submission — Triton-fused attention kernel.

This version uses a custom Triton kernel to fuse attention computation.
Falls back to matmul for small shapes (bs <= 4 or total_kv <= 32768).

DeepSeek R1 MLA parameters:
- Q dimension: 576 (KV_LORA_RANK 512 + QK_ROPE_HEAD_DIM 64)
- V dimension: 512 (KV_LORA_RANK)
- SM_SCALE: 1/sqrt(576)
- Tolerance: rtol=0.1, atol=0.1
"""

import torch
import triton
import triton.language as tl
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)
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
FP8_DTYPE = aiter_dtypes.fp8

# Routing thresholds
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

# Cache for metadata
_cache: dict = {}


def _choose_splits(total_kv: int) -> int:
    """Adaptive num_kv_splits based on KV length."""
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 131072:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Dynamic per-tensor FP8 quantization."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _get_meta(bs, qsl, kvsl, qdt, kvdt, qo_ind, kv_ind, splits):
    """Get or create cached metadata."""
    key = (bs, qsl, kvsl, qdt, kvdt, splits)
    if key in _cache:
        return _cache[key]

    nq, nkv = NUM_HEADS, NUM_KV_HEADS
    kv_last = (kv_ind[1:] - kv_ind[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(
        bs,
        qsl,
        nq,
        qdt,
        kvdt,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=splits,
        intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    wm, wi, wis, ri, rfm, rpm = work
    get_mla_metadata_v1(
        qo_ind,
        kv_ind,
        kv_last,
        nq // nkv,
        nkv,
        True,
        wm,
        wis,
        wi,
        ri,
        rfm,
        rpm,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qsl,
        uni_seqlen_qo=qsl,
        fast_mode=False,
        max_split_per_batch=splits,
        intra_batch_mode=True,
        dtype_q=qdt,
        dtype_kv=kvdt,
    )
    tq = bs * qsl
    tkv = int(kv_ind[-1].item())
    meta = {
        "wm": wm,
        "wi": wi,
        "wis": wis,
        "ri": ri,
        "rfm": rfm,
        "rpm": rpm,
        "kvi": torch.arange(tkv, dtype=torch.int32, device="cuda"),
        "kvl": kv_last,
        "logits": torch.empty((splits, tq, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda"),
        "lse": torch.empty((splits, tq, nq), dtype=torch.float32, device="cuda"),
        "out": torch.empty((tq, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"),
    }
    _cache[key] = meta
    return meta


@triton.jit
def mla_attention_kernel(
    Q,  # [total_q, num_heads, qk_dim]
    KV,  # [total_kv, num_kv_heads, qk_dim]
    Out,  # [total_q, num_heads, v_dim]
    qo_indptr,  # [batch_size + 1]
    kv_indptr,  # [batch_size + 1]
    NUM_HEADS: tl.constexpr,
    NUM_KV_HEADS: tl.constexpr,
    QK_HEAD_DIM: tl.constexpr,
    V_HEAD_DIM: tl.constexpr,
    SM_SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    """Triton MLA attention kernel with online softmax."""
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)

    q_start = tl.load(qo_indptr)
    q_end = tl.load(qo_indptr + 1)
    kv_start = tl.load(kv_indptr)
    kv_end = tl.load(kv_indptr + 1)

    seq_q = q_end - q_start
    seq_kv = kv_end - kv_start

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < seq_q

    # Online softmax accumulators
    m_i = tl.full([BLOCK_M], value=-float("inf"), dtype=tl.float32)
    l_i = tl.full([BLOCK_M], value=0.0, dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, V_HEAD_DIM], dtype=tl.float32)

    num_kv_blocks = tl.cdiv(seq_kv, BLOCK_N)

    for kv_block in range(0, num_kv_blocks):
        offs_n = kv_block * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_n = offs_n < seq_kv

        # Compute attention scores
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k_iter in range(tl.cdiv(QK_HEAD_DIM, 64)):
            offs_k = k_iter * 64 + tl.arange(0, 64)
            mask_k = offs_k < QK_HEAD_DIM

            # Load Q
            q_base = (q_start + offs_m[:, None]) * NUM_HEADS * QK_HEAD_DIM + pid_h * QK_HEAD_DIM
            q_ptrs = Q + q_base + offs_k[None, :]
            q_tile = tl.load(q_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)

            # Load K
            k_base = (kv_start + offs_n[:, None]) * NUM_KV_HEADS * QK_HEAD_DIM
            k_ptrs = KV + k_base + offs_k[None, :]
            k_tile = tl.load(k_ptrs, mask=mask_n[:, None] & mask_k[None, :], other=0.0)

            # Matmul
            qk += tl.dot(q_tile, tl.trans(k_tile), input_precision="tf32")

        qk *= SM_SCALE

        # Online softmax
        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        p = tl.exp(qk - m_ij[:, None])
        l_i = l_i * tl.exp(m_i - m_ij) + tl.sum(p, axis=1)
        m_i = m_ij

        # Attention: p @ V
        for v_iter in range(tl.cdiv(V_HEAD_DIM, 64)):
            offs_v = v_iter * 64 + tl.arange(0, 64)
            mask_v = offs_v < V_HEAD_DIM

            v_base = (kv_start + offs_n[:, None]) * NUM_KV_HEADS * QK_HEAD_DIM
            v_ptrs = KV + v_base + offs_v[None, :]
            v_tile = tl.load(v_ptrs, mask=mask_n[:, None] & mask_v[None, :], other=0.0)

            # Accumulate
            acc_slice = tl.dot(p, v_tile, out_dtype=tl.float32)

            for i in tl.static_range(0, BLOCK_M):
                for j in tl.static_range(0, 64):
                    if offs_v[j] < V_HEAD_DIM:
                        acc[i, offs_v[j]] += acc_slice[i, j]

    # Normalize and store
    acc = acc / l_i[:, None]

    for v_iter in range(tl.cdiv(V_HEAD_DIM, 64)):
        offs_v = v_iter * 64 + tl.arange(0, 64)
        mask_v = offs_v < V_HEAD_DIM

        out_base = offs_m[:, None] * NUM_HEADS * V_HEAD_DIM + pid_h * V_HEAD_DIM
        out_ptrs = Out + out_base + offs_v[None, :]

        out_vals = tl.zeros([BLOCK_M, 64], dtype=tl.bfloat16)
        for i in tl.static_range(0, BLOCK_M):
            for j in tl.static_range(0, 64):
                if offs_v[j] < V_HEAD_DIM:
                    out_vals[i, j] = tl.cast(acc[i, offs_v[j]], tl.bfloat16)

        tl.store(out_ptrs, out_vals, mask=mask_m[:, None] & mask_v[None, :])


def custom_kernel(data: input_t) -> output_t:
    """MLA decode with Triton kernel and matmul fallback."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qsl = config["q_seq_len"]
    kvsl = config["kv_seq_len"]
    total_q = bs * qsl
    total_kv = bs * kvsl

    # ── Regime 1: matmul for small shapes ──
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv = kv_data["bf16"]
        q3 = q.view(bs, NUM_HEADS, QK_HEAD_DIM)
        kv_b = kv.view(bs, kvsl, QK_HEAD_DIM)
        scores = torch.matmul(q3, kv_b.transpose(1, 2)).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1, dtype=torch.float32).to(torch.bfloat16)
        v_b = kv_b[:, :, :V_HEAD_DIM]
        return torch.matmul(weights, v_b).view(total_q, NUM_HEADS, V_HEAD_DIM)

    # ── Regime 2: Triton kernel for larger shapes ──
    kv_bf16 = kv_data["bf16"]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)

    output = torch.empty((total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    # Triton grid
    BLOCK_M = 64
    num_q_blocks = triton.cdiv(total_q, BLOCK_M)
    grid = (num_q_blocks, NUM_HEADS, bs)

    # Launch Triton kernel
    mla_attention_kernel[grid](
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
    )

    return output
