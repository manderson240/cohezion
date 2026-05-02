"""MLA Breakthrough: Fixed metadata API.

Target: 4.3µs (leader) vs current ~67µs
Strategy: Maximum parallelism with FP8 and optimized metadata
"""

import torch
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


SM_SCALE = 1.0 / (576**0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1
NUM_KV_SPLITS = 32


def custom_kernel(data: input_t) -> output_t:
    """Optimized MLA with maximum parallelism for MI355X."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]
    total_kv = bs * kvseqlen

    # FIX: Unpack the tuple - kv_data["fp8"] returns (tensor, scale)
    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    # Calculate optimal num_kv_splits based on K-Search formula
    if total_kv <= 2048:
        num_splits = 8
    elif total_kv <= 8192:
        num_splits = 16
    elif total_kv <= 32768:
        num_splits = 32
    elif total_kv <= 131072:
        num_splits = 64
    else:
        num_splits = 64  # Maximum

    o = torch.empty((q.shape[0], nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    # FIX: Proper metadata creation like reference implementation
    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        nheads,
        q.dtype,
        kv_fp8.dtype,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=num_splits,
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
        nheads // NUM_KV_HEADS,
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
        fast_mode=False,
        max_split_per_batch=num_splits,
        intra_batch_mode=True,
        dtype_q=q.dtype,
        dtype_kv=kv_fp8.dtype,
    )

    mla_decode_fwd(
        q.view(-1, nheads, QK_HEAD_DIM),
        kv_4d,
        o,
        qo_indptr,
        kv_indptr,
        kv_indices,
        kv_last_page_len,
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_splits,
        intra_batch_mode=True,
        work_meta_data=work_metadata,
        work_indptr=work_indptr,
        work_info_set=work_info_set,
        reduce_indptr=reduce_indptr,
        reduce_final_map=reduce_final_map,
        reduce_partial_map=reduce_partial_map,
    )
    return o
