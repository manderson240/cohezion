#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""
MLA: Ring Attention for Blockwise Computation

This kernel implements Ring Attention, which partitions long sequences
into blocks that can be processed in parallel while maintaining
global attention capability.

Key Innovation:
Standard attention: O(N^2) memory for NxN attention matrix
Ring attention: O(N/B * B^2) = O(N*B) for block size B

Algorithm:
1. Partition KV sequence into K blocks
2. Each query block attends to all KV blocks
3. Use online softmax for numerical stability
4. Accumulate attention across blocks

Ring Communication Pattern:
- Each query block processes KV blocks in ring order
- Accumulates max/logsum for online softmax
- Final output is globally consistent

Benefits:
- Memory: Linear in sequence length (with fixed block size)
- Parallelism: Independent block processing
- Scalability: Can handle 1M+ sequences
- Numerical: Online softmax maintains precision

Blockwise Computation:
- Process blocks one at a time
- Accumulate softmax statistics
- Correct normalization across blocks

Expected Performance:
- Long sequences (64K+): Significant memory savings
- Compute: Similar to standard attention
- Scalability: Linear memory growth
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

# Ring attention configuration
RING_BLOCK_SIZE = 1024  # Size of KV blocks

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


def _ring_attention(
    q: torch.Tensor,
    kv_bf16: torch.Tensor,
    bs: int,
    kvseqlen: int,
    block_size: int = RING_BLOCK_SIZE,
) -> torch.Tensor:
    """
    Compute ring attention with blockwise processing.

    Args:
        q: [total_q, NUM_HEADS, QK_HEAD_DIM] queries
        kv_bf16: [total_kv, 1, QK_HEAD_DIM] KV cache
        bs: batch size
        kvseqlen: KV sequence length
        block_size: Block size for KV

    Returns:
        output: [total_q, NUM_HEADS, V_HEAD_DIM] attention output
    """
    # Reshape
    q_reshaped = q.view(bs, NUM_HEADS, QK_HEAD_DIM)
    kv_reshaped = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)

    num_blocks = (kvseqlen + block_size - 1) // block_size

    # Online softmax statistics
    max_score = torch.full((bs, NUM_HEADS, 1), -1e10, device=q.device)
    sum_exp = torch.zeros(bs, NUM_HEADS, 1, device=q.device)
    numerator = torch.zeros(bs, NUM_HEADS, V_HEAD_DIM, device=q.device)

    # Process KV blocks in ring
    for b in range(num_blocks):
        kv_start = b * block_size
        kv_end = min((b + 1) * block_size, kvseqlen)

        # Extract KV block
        kv_block = kv_reshaped[:, kv_start:kv_end, :]  # [bs, block, head_dim]
        v_block = kv_block[:, :, :V_HEAD_DIM]  # [bs, block, v_dim]

        # Compute scores for this block
        scores = (
            torch.matmul(
                q_reshaped,  # [bs, heads, head_dim]
                kv_block.transpose(-1, -2),  # [bs, head_dim, block]
            )
            * SM_SCALE
        )  # [bs, heads, block]

        # Block-wise max
        block_max = scores.max(dim=-1, keepdim=True).values

        # Update running max
        new_max = torch.maximum(max_score, block_max)

        # Correct previous accumulator
        exp_correction = torch.exp(max_score - new_max)
        sum_exp = sum_exp * exp_correction
        numerator = numerator * exp_correction.squeeze(-1).unsqueeze(-1)

        # Add current block
        exp_scores = torch.exp(scores - new_max)
        sum_exp = sum_exp + exp_scores.sum(dim=-1, keepdim=True)
        numerator = numerator + torch.matmul(exp_scores, v_block)

        # Update max
        max_score = new_max

    # Final normalization
    output = numerator / (sum_exp.squeeze(-1).unsqueeze(-1) + 1e-10)

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
    """Ring attention MLA kernel with blockwise computation."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Small batches: einsum
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    # For long sequences, use ring attention
    if kvseqlen >= RING_BLOCK_SIZE * 2 and bs <= 64:
        try:
            kv_bf16 = kv_data["bf16"]
            return _ring_attention(q, kv_bf16, bs, kvseqlen)
        except Exception as e:
            print(f"[RingAttention] Error: {e}, falling back")

    # Default: ASM
    return _asm_attention(data)
