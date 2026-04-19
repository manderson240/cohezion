#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""
MLA: Sparse Block Attention

This kernel implements sparse block-wise attention for efficient processing
of long sequences. Instead of attending to all KV positions, we attend
to fixed-size blocks with configurable sparsity patterns.

Sparse Patterns:
1. Local attention: Attend to nearby tokens (sliding window)
2. Strided attention: Attend to every Nth token
3. Block sparse: Attend to dense blocks with gaps
4. Combination: Local + global tokens

Algorithm:
1. Partition KV cache into blocks
2. Select relevant blocks based on sparsity pattern
3. Compute attention only over selected blocks
4. Combine partial results

Block Selection Strategies:
  - Fixed blocks: Every k-th block
  - Query-dependent: Blocks with highest similarity to query
  - Hierarchical: Coarse-to-fine block selection
  - Learned: Pre-trained block importance scores

Memory Efficiency:
  - Attention complexity: O(N * sqrt(N)) instead of O(N^2)
  - Cache friendly: Contiguous block access
  - Scalable to very long sequences

Performance Characteristics:
  - Best for sequences > 4096 tokens
  - Trade-off: accuracy vs computation
  - Pattern selection critical for quality
  - Hardware-friendly: regular access patterns
"""

from __future__ import annotations
import os
import math

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

import torch
from task import input_t, output_t

# Import aiter for fallback
import aiter
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1

# Sparse block configuration
BLOCK_SIZE = 256  # Tokens per block
LOCAL_WINDOW_BLOCKS = 4  # Number of local blocks to attend
STRIDE_FACTOR = 4  # Strided attention: every 4th block
NUM_HEADS = 16
QK_DIM = 576
V_DIM = 512
PAGE_SIZE = 1
SM_SCALE = 1.0 / (QK_DIM**0.5)
FP8_DTYPE = aiter_dtypes.fp8


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Quantize tensor to FP8 format."""
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _select_sparse_blocks(
    q: torch.Tensor,
    kv: torch.Tensor,
    kv_indptr: torch.Tensor,
    batch_size: int,
    kv_seq_len: int,
    pattern: str = "local_strided",
) -> list[list[int]]:
    """
    Select which KV blocks to attend based on sparsity pattern.

    Patterns:
    - "local": Attend to window around query position
    - "strided": Attend to every Nth block
    - "local_strided": Local + strided blocks
    - "block_sparse": Fixed block pattern

    Args:
        q: Query tensor [total_q, NUM_HEADS, QK_DIM]
        kv: KV tensor [total_kv, QK_DIM]
        kv_indptr: [batch_size+1] KV boundaries
        batch_size: Batch size
        kv_seq_len: KV sequence length per batch
        pattern: Sparsity pattern to use

    Returns:
        selected_blocks: List of block indices per batch
    """
    device = q.device
    num_blocks = (kv_seq_len + BLOCK_SIZE - 1) // BLOCK_SIZE

    batch_blocks = []

    for b in range(batch_size):
        kv_start = kv_indptr[b].item()
        kv_end = kv_indptr[b + 1].item()
        num_batch_blocks = (kv_end - kv_start + BLOCK_SIZE - 1) // BLOCK_SIZE

        selected = set()

        if pattern in ["local", "local_strided"]:
            # Local window: last LOCAL_WINDOW_BLOCKS
            for i in range(max(0, num_batch_blocks - LOCAL_WINDOW_BLOCKS), num_batch_blocks):
                selected.add(i)

        if pattern in ["strided", "local_strided"]:
            # Strided: every STRIDE_FACTOR-th block
            for i in range(0, num_batch_blocks, STRIDE_FACTOR):
                selected.add(i)

        if pattern == "block_sparse":
            # Sparse pattern: alternate dense and sparse
            for i in range(0, num_batch_blocks):
                if i % 2 == 0 or i >= num_batch_blocks - LOCAL_WINDOW_BLOCKS:
                    selected.add(i)

        # Always include last block (most recent context)
        selected.add(num_batch_blocks - 1)

        batch_blocks.append(sorted(list(selected)))

    return batch_blocks


def _compute_sparse_attention(
    q: torch.Tensor,
    kv_data: dict,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    selected_blocks: list[list[int]],
    config: dict,
) -> torch.Tensor:
    """
    Compute attention over selected sparse blocks.

    Args:
        q: Query tensor [total_q, NUM_HEADS, QK_DIM]
        kv_data: KV cache dictionary
        qo_indptr: Query/Output boundaries
        kv_indptr: KV boundaries
        selected_blocks: Selected block indices per batch
        config: Model configuration

    Returns:
        output: Attention output [total_q, NUM_HEADS, V_DIM]
    """
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_q = bs  # decode: qseqlen=1
    total_kv = bs * kvseqlen

    device = q.device

    # Get KV in bf16
    kv_bf16 = kv_data["bf16"].view(total_kv, QK_DIM)

    # Initialize accumulators for online softmax
    output = torch.zeros(total_q, NUM_HEADS, V_DIM, dtype=torch.bfloat16, device=device)

    for b in range(bs):
        q_idx = b
        kv_start = kv_indptr[b].item()

        for h in range(NUM_HEADS):
            q_vec = q[q_idx, h, :]  # [QK_DIM]

            # Online softmax accumulators
            running_max = torch.tensor(-1e30, device=device)
            running_sum = torch.tensor(0.0, device=device)
            acc_v = torch.zeros(V_DIM, device=device)

            # Iterate over selected blocks
            for block_idx in selected_blocks[b]:
                block_start = kv_start + block_idx * BLOCK_SIZE
                block_end = min(block_start + BLOCK_SIZE, kv_indptr[b + 1].item())

                if block_start >= block_end:
                    continue

                # Get KV for this block
                kv_block = kv_bf16[block_start:block_end, :]  # [block_len, QK_DIM]

                # Compute scores: q @ K^T
                scores = torch.matmul(q_vec.unsqueeze(0), kv_block.T).squeeze(0)  # [block_len]
                scores = scores * SM_SCALE

                # Online softmax update
                block_max = scores.max()
                new_max = torch.maximum(running_max, block_max)

                # Rescale previous accumulation
                exp_correction = torch.exp(running_max - new_max)
                running_sum = running_sum * exp_correction
                acc_v = acc_v * exp_correction

                # Add current block
                exp_scores = torch.exp(scores - new_max)
                running_sum = running_sum + exp_scores.sum()

                # Get V values (first V_DIM of KV)
                v_block = kv_block[:, :V_DIM]  # [block_len, V_DIM]
                acc_v = acc_v + torch.matmul(exp_scores.unsqueeze(0), v_block).squeeze(0)

                running_max = new_max

            # Normalize and write output
            if running_sum > 0:
                output[q_idx, h, :] = (acc_v / running_sum).to(torch.bfloat16)

    return output


def _choose_num_kv_splits(total_kv: int) -> int:
    """Choose number of KV splits based on sequence length."""
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 65536:
        return 8
    return 16


def _asm_attention(data: input_t) -> torch.Tensor:
    """ASM-based attention for medium shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    num_kv_splits = _choose_num_kv_splits(total_kv)

    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, 1, QK_DIM)
    key = (bs, qseqlen, kvseqlen, q_fp8.dtype, kv_buffer_fp8.dtype, num_kv_splits)

    cache = {}
    if key not in cache:
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
        cache[key] = {
            "work_metadata": wm,
            "work_indptr": wi,
            "work_info_set": ws,
            "reduce_indptr": ri,
            "reduce_final_map": rf,
            "reduce_partial_map": rp,
            "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
            "kv_last_page_len": kv_last_page_len,
            "logits": torch.empty(
                (num_kv_splits, total_q_val, NUM_HEADS, V_DIM), dtype=torch.float32, device="cuda"
            ),
            "attn_lse": torch.empty(
                (num_kv_splits, total_q_val, NUM_HEADS), dtype=torch.float32, device="cuda"
            ),
            "output": torch.empty(
                (total_q_val, NUM_HEADS, V_DIM), dtype=torch.bfloat16, device="cuda"
            ),
        }

    meta = cache[key]
    output = meta["output"]

    aiter.mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_DIM),
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


def _einsum_attention(data: input_t) -> torch.Tensor:
    """Standard einsum attention for small shapes."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v).reshape(-1, NUM_HEADS, V_DIM).to(torch.bfloat16)
    )


def custom_kernel(data: input_t) -> output_t:
    """
    Sparse block attention kernel.

    Implements attention over selected blocks to reduce
    computation for long sequences.
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Use einsum for small sequences
    if bs <= 4 or total_kv <= 4096:
        return _einsum_attention(data)

    # For very long sequences, use sparse block attention
    if total_kv >= 8192:
        try:
            # Select sparse blocks
            selected_blocks = _select_sparse_blocks(
                q, kv_data["bf16"], kv_indptr, bs, kvseqlen, pattern="local_strided"
            )

            # Compute sparse attention
            output = _compute_sparse_attention(
                q, kv_data, qo_indptr, kv_indptr, selected_blocks, config
            )

            return output

        except Exception as e:
            print(f"[SparseBlocks] Sparse attention failed: {e}, using fallback")

    # Fallback to ASM attention
    try:
        return _asm_attention(data)
    except Exception as e:
        print(f"[SparseBlocks] ASM fallback failed: {e}, using einsum")
        return _einsum_attention(data)
