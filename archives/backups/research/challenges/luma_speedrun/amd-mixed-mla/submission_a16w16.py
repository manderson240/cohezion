#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""A16W16: BF16 Q + BF16 KV via mla_decode_stage1_asm_fwd directly.

Key insight: the runner has mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co — a
dedicated BF16 (a16w16) decode stage1 kernel for 16 query heads. By passing
BF16 tensors with q_scale=None and kv_scale=None, mla_decode_stage1_asm_fwd
dispatches to this kernel, skipping ALL FP8 overhead:
  - No _quantize_fp8(q) call
  - No kv_scale computation
  - No FP8 dequantize step inside the ASM kernel

vs submission_bf16_only.py (which uses mla_decode_fwd wrapper):
  - Calls mla_decode_stage1_asm_fwd + mla_reduce_v1 directly, avoiding the
    Python wrapper overhead in mla_decode_fwd.

Retains:
  - fast_mode=True (10% tolerance allows it, proven in A7/A8)
  - Shape-tuned num_kv_splits from A8
  - Einsum for smallest shape (total_kv <= 4096)
"""

import torch
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)
from task import input_t, output_t


NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1

EINSUM_MAX_TOTAL_KV = 4096

_cache: dict = {}


def _choose_num_kv_splits(total_kv: int) -> int:
    if total_kv <= 4096:
        return 1
    if total_kv <= 32768:
        return 4
    if total_kv <= 65536:
        return 4
    if total_kv <= 262144:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _get_cached_metadata_bf16(
    bs: int,
    qseqlen: int,
    kvseqlen: int,
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    num_kv_splits: int,
) -> dict:
    """Allocate and populate work buffers for BF16 a16w16 stage1 decode."""
    key = ("a16w16", bs, qseqlen, kvseqlen, num_kv_splits)
    if key in _cache:
        return _cache[key]

    bf16 = torch.bfloat16
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        NUM_HEADS,
        bf16,
        bf16,
        is_sparse=False,
        fast_mode=True,
        num_kv_splits=num_kv_splits,
        intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    (
        work_metadata,
        work_indptr,
        work_info_set,
        reduce_indptr,
        reduce_final_map,
        reduce_partial_map,
    ) = work

    get_mla_metadata_v1(
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        NUM_HEADS // NUM_KV_HEADS,
        NUM_KV_HEADS,
        True,
        work_metadata,
        work_info_set,
        work_indptr,
        reduce_indptr,
        reduce_final_map,
        reduce_partial_map,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen,
        uni_seqlen_qo=qseqlen,
        fast_mode=True,
        max_split_per_batch=num_kv_splits,
        intra_batch_mode=True,
        dtype_q=bf16,
        dtype_kv=bf16,
    )

    total_kv_len = int(kv_indptr[-1].item())
    total_q = bs * qseqlen

    meta = {
        "work_meta_data": work_metadata,
        "work_indptr": work_indptr,
        "work_info_set": work_info_set,
        "reduce_indptr": reduce_indptr,
        "reduce_final_map": reduce_final_map,
        "reduce_partial_map": reduce_partial_map,
        "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
        "kv_last_page_len": kv_last_page_len,
        "logits": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.float32,
            device="cuda",
        ),
        "attn_lse": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS),
            dtype=torch.float32,
            device="cuda",
        ),
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        ),
    }
    _cache[key] = meta
    return meta


def _einsum_attention(data: input_t) -> output_t:
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


def _a16w16_attention(data: input_t) -> output_t:
    """BF16 Q + BF16 KV via direct stage1 ASM dispatch (no FP8 overhead)."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_bf16 = kv_data["bf16"]
    num_kv_splits = _choose_num_kv_splits(total_kv)

    # 4D view: (total_kv, page_size=1, nhead_kv=1, dim=576)
    kv_4d = kv_bf16.view(kv_bf16.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _get_cached_metadata_bf16(bs, qseqlen, kvseqlen, qo_indptr, kv_indptr, num_kv_splits)

    output = meta["output"]
    logits = meta["logits"]
    attn_lse = meta["attn_lse"]

    # Direct ASM dispatch: BF16 Q + BF16 KV, no scale tensors required.
    # Routes to mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co on the runner.
    mla_decode_stage1_asm_fwd(
        q.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        None,  # num_kv_splits_indptr (None = uniform)
        meta["work_meta_data"],
        meta["work_indptr"],
        meta["work_info_set"],
        qseqlen,
        PAGE_SIZE,
        NUM_KV_HEADS,
        SM_SCALE,
        logits,
        attn_lse,
        output,
        None,  # q_scale = None for BF16 Q
        None,  # kv_scale = None for BF16 KV
    )

    mla_reduce_v1(
        logits,
        attn_lse,
        meta["reduce_indptr"],
        meta["reduce_final_map"],
        meta["reduce_partial_map"],
        qseqlen,
        output,
        None,
    )

    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    if total_kv <= EINSUM_MAX_TOTAL_KV:
        return _einsum_attention(data)

    return _a16w16_attention(data)
