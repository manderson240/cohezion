"""MLA v10 - Aggressive parallelism for large sequences."""

import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from task import input_t, output_t


SM_SCALE = 1.0 / (576**0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8


def _choose_num_kv_splits(total_kv: int) -> int:
    """Aggressive splits for larger sequences."""
    if total_kv <= 1024:
        return 1
    elif total_kv <= 8192:
        return 4
    elif total_kv <= 65536:
        return 16
    elif total_kv <= 262144:
        return 32
    return 64  # Maximum splits for very large sequences


def custom_kernel(data: input_t) -> output_t:
    """Aggressive MLA with high parallelism."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]
    total_kv = bs * kvseqlen

    # Always use FP8 path for speed
    kv_fp8, kv_scale = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])

    num_splits = _choose_num_kv_splits(total_kv)

    # Quantize Q to FP8 for speed
    finfo = torch.finfo(FP8_DTYPE)
    amax = q.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    q_input = (q / scale).clamp(finfo.min, finfo.max).to(FP8_DTYPE)
    q_scale = scale.float().reshape(1)

    o = torch.empty((q.shape[0], nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    # Build metadata
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        nheads,
        FP8_DTYPE,
        FP8_DTYPE,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=num_splits,
        intra_batch_mode=True,
    )
    wm, wi, wis, ri, rfm, rpm = [torch.empty(s, dtype=t, device="cuda") for s, t in info]

    get_mla_metadata_v1(
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        nheads // NUM_KV_HEADS,
        NUM_KV_HEADS,
        True,
        wm,
        wis,
        wi,
        ri,
        rfm,
        rpm,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen,
        uni_seqlen_qo=qseqlen,
        fast_mode=False,
        max_split_per_batch=num_splits,
        intra_batch_mode=True,
        dtype_q=FP8_DTYPE,
        dtype_kv=FP8_DTYPE,
    )

    # Try direct ASM dispatch
    try:
        import aiter

        if hasattr(aiter, "mla_decode_stage1_asm_fwd"):
            stage1_fn = aiter.mla_decode_stage1_asm_fwd
            reduce_fn = aiter.mla_reduce_v1

            split_data = torch.empty(
                (q.shape[0], num_splits, nheads, V_HEAD_DIM + 8),
                dtype=torch.float32,
                device="cuda",
            )
            split_lse = torch.empty(
                (q.shape[0], num_splits, nheads),
                dtype=torch.float32,
                device="cuda",
            )

            stage1_fn(
                q_input.view(-1, nheads, QK_HEAD_DIM),
                kv_4d,
                qo_indptr,
                kv_indptr,
                kv_indices,
                kv_last_page_len,
                None,
                wm,
                wi,
                wis,
                qseqlen,
                PAGE_SIZE,
                NUM_KV_HEADS,
                SM_SCALE,
                split_data,
                split_lse,
                o,
                q_scale=q_scale,
                kv_scale=kv_scale,
            )

            reduce_fn(
                split_data,
                split_lse,
                ri,
                rfm,
                rpm,
                qseqlen,
                o,
            )
            return o
    except:
        pass

    # Fallback to mla_decode_fwd
    from aiter.mla import mla_decode_fwd

    mla_decode_fwd(
        q_input.view(-1, nheads, QK_HEAD_DIM),
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
        q_scale=q_scale,
        kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=wm,
        work_indptr=wi,
        work_info_set=wis,
        reduce_indptr=ri,
        reduce_final_map=rfm,
        reduce_partial_map=rpm,
    )
    return o
