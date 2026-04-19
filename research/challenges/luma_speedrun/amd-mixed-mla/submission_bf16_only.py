#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""Approach A: BF16-only attention — skip FP8 quantization entirely.

The 10% error tolerance is very relaxed. By using BF16 Q and KV directly we
eliminate:
  - Q FP8 quantization (~1-2us GPU compute)
  - kv_scale scalar computation
  - The FP8 dequantize step inside the ASM kernel

The reference confirms BF16 Q + BF16 KV is a valid path (Q_DTYPE="bf16",
KV_DTYPE="bf16"). We pass q_scale=None and kv_scale=None.

Still uses fast_mode=True (from A7/A8) and shape-tuned num_kv_splits.
Einsum for the smallest shape (total_kv <= 4096).
"""

import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
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


def _get_cached_metadata_bf16(bs, qseqlen, kvseqlen, qo_indptr, kv_indptr, num_kv_splits):
    """Metadata for BF16 Q + BF16 KV (no FP8)."""
    key = ("bf16", bs, qseqlen, kvseqlen, num_kv_splits)
    if key in _cache:
        return _cache[key]

    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    bf16_dtype = torch.bfloat16
    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        NUM_HEADS,
        bf16_dtype,
        bf16_dtype,
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
        dtype_q=bf16_dtype,
        dtype_kv=bf16_dtype,
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
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        ),
    }
    _cache[key] = meta
    return meta


def _einsum_attention(data):
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


def _bf16_attention(data):
    """ASM path with BF16 Q and BF16 KV — no quantization overhead."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_bf16 = kv_data["bf16"]
    num_kv_splits = _choose_num_kv_splits(total_kv)

    # 4D view: (total_kv, page_size=1, nhead_kv=1, dim=576)
    kv_4d = kv_bf16.view(kv_bf16.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _get_cached_metadata_bf16(
        bs,
        qseqlen,
        kvseqlen,
        qo_indptr,
        kv_indptr,
        num_kv_splits,
    )
    output = meta["output"]

    mla_decode_fwd(
        q.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        output,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_kv_splits,
        q_scale=None,
        kv_scale=None,
        intra_batch_mode=True,
        **{
            k: meta[k]
            for k in [
                "work_meta_data",
                "work_indptr",
                "work_info_set",
                "reduce_indptr",
                "reduce_final_map",
                "reduce_partial_map",
            ]
        },
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    if total_kv <= EINSUM_MAX_TOTAL_KV:
        return _einsum_attention(data)

    return _bf16_attention(data)
