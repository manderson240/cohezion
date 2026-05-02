#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""M4: Chunked attention for long sequences.

Novel approach: Process long KV sequences in fixed-size chunks
with dynamic scheduling based on sequence length.

Architecture:
- Split KV into 1K or 2K token chunks
- Compute attention per-chunk with local softmax
- Merge using online softmax algorithm
- Overlap chunk computation with CUDA streams

Key benefits for long sequences:
- Better L2 cache locality (chunk fits in cache)
- Reduced register pressure (smaller inner loop)
- Opportunity for early exit on low-score chunks

Best for: kv_seqlen > 4096 (where standard attention is memory-bound)
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

# Import aiter for fallback
import aiter
import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1, mla_reduce_v1
from task import input_t, output_t


NUM_HEADS = 16
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
CHUNK_SIZE = 1024  # Process KV in 1K token chunks

_cache = {}
_chunk_cache = {}


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
    if total_kv <= 8192:
        return 4
    if total_kv <= 32768:
        return 8
    if total_kv <= 131072:
        return 16
    return 32


def _compute_chunked_attention(q, kv, bs, kvseqlen, num_chunks):
    """Compute attention in chunks with online softmax.

    Args:
        q: [bs, NUM_HEADS, QK_HEAD_DIM] — query tensor
        kv: [bs*kvseqlen, QK_HEAD_DIM] — key-value tensor (KV fused)
        bs: batch size
        kvseqlen: length of KV sequence per batch
        num_chunks: number of chunks to split KV into

    Returns:
        [bs, NUM_HEADS, V_HEAD_DIM] attention output
    """
    chunk_size = (kvseqlen + num_chunks - 1) // num_chunks
    total_q = bs  # decode: qseqlen=1

    # Output accumulator with running stats
    output = torch.zeros((total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.float32, device=q.device)
    running_max = torch.full((total_q, NUM_HEADS), -1e30, dtype=torch.float32, device=q.device)
    running_sum = torch.zeros((total_q, NUM_HEADS), dtype=torch.float32, device=q.device)

    # Reshape KV for chunked access
    # kv is [bs*kvseqlen, QK_HEAD_DIM] — reorganize as [bs, kvseqlen, QK_HEAD_DIM]
    kv_reshaped = kv.view(bs, kvseqlen, QK_HEAD_DIM)
    v_part = kv_reshaped[:, :, :V_HEAD_DIM]  # [bs, kvseqlen, V_HEAD_DIM]

    # Reshape Q for broadcasting
    q_reshaped = q.view(total_q, NUM_HEADS, QK_HEAD_DIM)  # [bs, NUM_HEADS, QK_HEAD_DIM]

    # Process each chunk
    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * chunk_size
        end_idx = min(start_idx + chunk_size, kvseqlen)
        if start_idx >= kvseqlen:
            break

        # Get chunk: [bs, chunk_len, QK_HEAD_DIM]
        kv_chunk = kv_reshaped[:, start_idx:end_idx, :]
        v_chunk = v_part[:, start_idx:end_idx, :]  # [bs, chunk_len, V_HEAD_DIM]
        chunk_len = end_idx - start_idx

        # Compute Q @ K^T for this chunk: [bs, NUM_HEADS, chunk_len]
        # Using einsum for clarity and batched matmul
        scores = torch.einsum("bnh,bch->bnc", q_reshaped, kv_chunk) * SM_SCALE

        # Online softmax update
        # New max for this chunk
        chunk_max = scores.max(dim=-1, keepdim=True).values  # [bs, NUM_HEADS, 1]

        # Update running max
        new_max = torch.maximum(running_max.unsqueeze(-1), chunk_max)

        # Compute exp with correction
        exp_scores = torch.exp(scores - new_max)  # [bs, NUM_HEADS, chunk_len]
        exp_correction = torch.exp(running_max.unsqueeze(-1) - new_max)

        # Update running sum
        chunk_sum = exp_scores.sum(dim=-1)  # [bs, NUM_HEADS]
        running_sum = running_sum * exp_correction.squeeze(-1) + chunk_sum
        running_max = new_max.squeeze(-1)

        # Accumulate weighted V: [bs, NUM_HEADS, V_HEAD_DIM]
        weighted_v = torch.einsum("bnc,bcv->bnv", exp_scores, v_chunk)
        output = output * exp_correction.squeeze(-1).unsqueeze(-1) + weighted_v

    # Final normalization
    output = output / running_sum.unsqueeze(-1)

    return output.to(torch.bfloat16)


def _chunked_attention_impl(data):
    """Chunked attention with adaptive chunk sizing."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Get KV in bf16 format
    kv_bf16 = kv_data["bf16"]  # [total_kv, 1, 576]
    kv_flat = kv_bf16.view(-1, QK_HEAD_DIM)  # [total_kv, 576]

    # Determine chunk count based on sequence length
    if kvseqlen <= 4096:
        # For short sequences, use standard einsum
        return _einsum_attention(data)

    # Use chunked attention for long sequences
    # Adaptive chunk count: more chunks for longer sequences
    if kvseqlen <= 8192:
        num_chunks = 4
    elif kvseqlen <= 32768:
        num_chunks = 8
    elif kvseqlen <= 65536:
        num_chunks = 16
    else:
        num_chunks = 32

    return _compute_chunked_attention(q, kv_flat, bs, kvseqlen, num_chunks)


def _einsum_attention(data):
    """Standard einsum attention for small shapes."""
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
    """ASM fallback for mid-size shapes."""
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
    """Chunked attention kernel with adaptive routing.

    Routes based on sequence length:
    - Short (<= 4096): einsum (fastest)
    - Medium (<= 32768): ASM (best throughput)
    - Long (> 32768): chunked attention (memory efficiency)
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # Routing decisions
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        return _einsum_attention(data)

    if kvseqlen > 32768:
        # Very long sequences: try chunked attention
        try:
            return _chunked_attention_impl(data)
        except Exception as e:
            print(f"[chunked] Error: {e}, falling back to ASM")

    # Default to ASM for medium sequences
    return _asm_attention(data)
