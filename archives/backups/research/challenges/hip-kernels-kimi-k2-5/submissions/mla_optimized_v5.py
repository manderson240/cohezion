"""MLA v5: Maximum aggression."""

import torch
from aiter import get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


SM_SCALE = 1.0 / (576**0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]
    total_kv = bs * kvseqlen

    kv_fp8 = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    # Maximum splits
    if total_kv <= 2048:
        num_splits = 8
    elif total_kv <= 8192:
        num_splits = 16
    elif total_kv <= 32768:
        num_splits = 32
    elif total_kv <= 131072:
        num_splits = 64
    else:
        num_splits = 64

    o = torch.empty((q.shape[0], nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    meta = get_mla_metadata_v1(
        bs,
        qseqlen,
        nheads,
        q.dtype,
        kv_fp8.dtype,
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        num_kv_splits=num_splits,
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
        **meta,
    )
    return o
