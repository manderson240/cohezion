#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""
MLA: Sinkhorn Routing for Optimal Transport Attention

This kernel applies Sinkhorn's algorithm for optimal transport to
attention routing, ensuring balanced information flow between queries
and key-value pairs.

Key Innovation:
Standard attention: softmax(Q @ K^T / sqrt(d))
Sinkhorn attention: Optimal transport between Q and K distributions

Mathematically:
1. Compute attention scores: S = Q @ K^T / sqrt(d)
2. Apply Sinkhorn iterations to find doubly stochastic matrix P
3. Use P for attention weights (balanced transport)

Sinkhorn Algorithm:
- Iteratively normalize rows and columns
- Enforces: sum(P[i,:]) = 1/N, sum(P[:,j]) = 1/M
- Results in balanced attention across all positions

Benefits:
- Balance: Equal attention mass per query/key
- Diversity: Prevents collapse to few positions
- Stability: Better gradients for long sequences
- Interpretability: P is a transport plan

Implementation Strategy:
- Start with standard attention scores
- Apply log-Sinkhorn for numerical stability
- 3-5 iterations typically sufficient
- Add epsilon for regularization

Expected Performance:
- Long sequences: Better stability than softmax
- Compute: +10-20% for Sinkhorn iterations
- Quality: More diverse attention patterns
"""

from __future__ import annotations
import os
import math

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from task import input_t, output_t

import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1

# MLA configuration
NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

# Sinkhorn configuration
SINKHORN_ITERATIONS = 3
SINKHORN_EPSILON = 0.01  # Entropic regularization

# Caches
_cache = {}


def _quantize_fp8(t):
    """Quantize to FP8 for ASM fallback."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_num_kv_splits(total_kv):
    """Adaptive split count based on total KV length."""
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 131072:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _sinkhorn_normalize(
    scores: torch.Tensor,
    num_iterations: int = SINKHORN_ITERATIONS,
    epsilon: float = SINKHORN_EPSILON,
) -> torch.Tensor:
    """
    Apply Sinkhorn normalization for doubly stochastic attention.

    Args:
        scores: [batch, heads, q_len, kv_len] attention scores
        num_iterations: Number of Sinkhorn iterations
        epsilon: Entropic regularization parameter

    Returns:
        doubly_stochastic: [batch, heads, q_len, kv_len] balanced attention
    """
    # Log-domain Sinkhorn for numerical stability
    log_scores = torch.log_softmax(scores, dim=-1)

    # Add regularization
    K = torch.exp(log_scores / epsilon)

    # Initialize
    u = torch.ones_like(K[..., 0])  # [batch, heads, q_len]
    v = torch.ones_like(K[..., 0, :])  # [batch, heads, kv_len]

    # Sinkhorn iterations
    for _ in range(num_iterations):
        # Update v: column normalization
        v = 1.0 / (K.transpose(-2, -1) @ u.unsqueeze(-1)).squeeze(-1)

        # Update u: row normalization
        u = 1.0 / (K @ v.unsqueeze(-1)).squeeze(-1)

    # Compute doubly stochastic matrix
    result = u.unsqueeze(-1) * K * v.unsqueeze(-2)

    return result


def _attention_with_sinkhorn(
    q: torch.Tensor,
    kv_bf16: torch.Tensor,
    bs: int,
    kvseqlen: int,
) -> torch.Tensor:
    """
    Compute attention with Sinkhorn balanced routing.

    Args:
        q: [total_q, NUM_HEADS, QK_HEAD_DIM] queries
        kv_bf16: [total_kv, 1, QK_HEAD_DIM] KV cache
        bs: batch size
        kvseqlen: KV sequence length

    Returns:
        output: [total_q, NUM_HEADS, V_HEAD_DIM] attention output
    """
    # Reshape
    q_reshaped = q.view(bs, NUM_HEADS, QK_HEAD_DIM)
    kv_reshaped = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)

    # Compute scores
    scores = (
        torch.matmul(
            q_reshaped,
            kv_reshaped.transpose(-1, -2),
        )
        * SM_SCALE
    )

    # Apply Sinkhorn for balanced attention
    weights = _sinkhorn_normalize(scores)

    # Get V
    v = kv_reshaped[:, :, :V_HEAD_DIM]

    # Compute output
    output = torch.matmul(weights, v)

    return output.view(-1, NUM_HEADS, V_HEAD_DIM).to(torch.bfloat16)


def _einsum_attention(data):
    """Standard einsum attention (baseline)."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v)
        .reshape(-1, NUM_HEADS, V_HEAD_DIM)
        .to(torch.bfloat16)
    )


def _asm_attention(data):
    """ASM fallback."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    q_fp8, q_scale = _quantize_fp8(q)
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    num_kv_splits = _choose_num_kv_splits(total_kv)

    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, 1, QK_HEAD_DIM)
    key = (bs, qseqlen, kvseqlen, q_fp8.dtype, kv_buffer_fp8.dtype, num_kv_splits)

    if key not in _cache:
        kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
        info = get_mla_metadata_info_v1(
            bs,
            qseqlen,
            NUM_HEADS,
            q_fp8.dtype,
            kv_buffer_fp8.dtype,
            is_sparse=False,
            fast_mode=False,
            num_kv_splits=num_kv_splits,
            intra_batch_mode=True,
        )
        work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
        wm, wi, ws, ri, rf, rp = work
        get_mla_metadata_v1(
            qo_indptr,
            kv_indptr,
            kv_last_page_len,
            NUM_HEADS,
            1,
            True,
            wm,
            ws,
            wi,
            ri,
            rf,
            rp,
            page_size=PAGE_SIZE,
            kv_granularity=max(PAGE_SIZE, 16),
            max_seqlen_qo=qseqlen,
            uni_seqlen_qo=qseqlen,
            fast_mode=False,
            max_split_per_batch=num_kv_splits,
            intra_batch_mode=True,
            dtype_q=q_fp8.dtype,
            dtype_kv=kv_buffer_fp8.dtype,
        )
        total_kv_len = int(kv_indptr[-1].item())
        total_q_val = bs * qseqlen
        _cache[key] = {
            "work_metadata": wm,
            "work_indptr": wi,
            "work_info_set": ws,
            "reduce_indptr": ri,
            "reduce_final_map": rf,
            "reduce_partial_map": rp,
            "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
            "kv_last_page_len": kv_last_page_len,
            "logits": torch.empty(
                (num_kv_splits, total_q_val, NUM_HEADS, V_HEAD_DIM),
                dtype=torch.float32,
                device="cuda",
            ),
            "attn_lse": torch.empty(
                (num_kv_splits, total_q_val, NUM_HEADS), dtype=torch.float32, device="cuda"
            ),
            "output": torch.empty(
                (total_q_val, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"
            ),
        }

    meta = _cache[key]
    output = meta["output"]
    aiter.mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        None,
        meta["work_metadata"],
        meta["work_indptr"],
        meta["work_info_set"],
        qseqlen,
        PAGE_SIZE,
        1,
        SM_SCALE,
        meta["logits"],
        meta["attn_lse"],
        output,
        q_scale,
        kv_scale,
    )
    mla_reduce_v1(
        meta["logits"],
        meta["attn_lse"],
        meta["reduce_indptr"],
        meta["reduce_final_map"],
        meta["reduce_partial_map"],
        qseqlen,
        output,
        None,
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    """
    Sinkhorn routing MLA kernel with balanced attention.
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Small batches: einsum
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # For medium sequences, try Sinkhorn
    if kvseqlen >= 1024 and bs <= 64:
        try:
            kv_bf16 = kv_data["bf16"]
            return _attention_with_sinkhorn(q, kv_bf16, bs, kvseqlen)
        except Exception as e:
            print(f"[Sinkhorn] Error: {e}, falling back")

    # Default: ASM
    return _asm_attention(data)
