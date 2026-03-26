"""MLA decode submission — fast_mode=True variant for A/B comparison.

Changes vs submission.py (baseline fast_mode=False):
- get_mla_metadata_info_v1: fast_mode=True
- get_mla_metadata_v1: fast_mode=True

fast_mode selects a different work distribution path inside aiter's persistent
scheduler. fast_mode=False was chosen heuristically ("CU work distribution is
better") without benchmarking; this variant tests that assumption.

Current baseline: ~69.7µs | Leader: ~33.0µs
"""

import torch
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

# ── Routing thresholds (Phase 11+14 tuned) ──
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768

# ── Metadata + intermediate cache ──
_cache: dict = {}


def _choose_num_kv_splits(total_kv: int) -> int:
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 131072:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _quantize_fp8(tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = tensor.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _get_cached_metadata(
    bs: int, qseqlen: int, kvseqlen: int,
    q_dtype: torch.dtype, kv_dtype: torch.dtype,
    qo_indptr: torch.Tensor, kv_indptr: torch.Tensor,
    num_kv_splits: int,
):
    key = (bs, qseqlen, kvseqlen, q_dtype, kv_dtype, num_kv_splits)
    if key in _cache:
        return _cache[key]

    nq, nkv = NUM_HEADS, NUM_KV_HEADS
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs, qseqlen, nq, q_dtype, kv_dtype,
        is_sparse=False, fast_mode=True,          # changed from False
        num_kv_splits=num_kv_splits, intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    work_metadata, work_indptr, work_info_set, reduce_indptr, reduce_final_map, reduce_partial_map = work

    get_mla_metadata_v1(
        qo_indptr, kv_indptr, kv_last_page_len,
        nq // nkv, nkv, True,
        work_metadata, work_info_set, work_indptr,
        reduce_indptr, reduce_final_map, reduce_partial_map,
        page_size=PAGE_SIZE, kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen, uni_seqlen_qo=qseqlen,
        fast_mode=True, max_split_per_batch=num_kv_splits,   # changed from False
        intra_batch_mode=True, dtype_q=q_dtype, dtype_kv=kv_dtype,
    )

    total_kv_len = int(kv_indptr[-1].item())
    kv_indices = torch.arange(total_kv_len, dtype=torch.int32, device="cuda")

    # Pre-allocate intermediates
    total_q = bs * qseqlen
    logits = torch.empty((num_kv_splits, total_q, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda")
    attn_lse = torch.empty((num_kv_splits, total_q, nq), dtype=torch.float32, device="cuda")
    output = torch.empty((total_q, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    meta = {
        "work_meta_data": work_metadata,
        "work_indptr": work_indptr,
        "work_info_set": work_info_set,
        "reduce_indptr": reduce_indptr,
        "reduce_final_map": reduce_final_map,
        "reduce_partial_map": reduce_partial_map,
        "kv_indices": kv_indices,
        "kv_last_page_len": kv_last_page_len,
        "logits": logits,
        "attn_lse": attn_lse,
        "output": output,
    }
    _cache[key] = meta
    return meta


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    # ── Regime 1: torch.matmul for small shapes ──
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv_bf16 = kv_data["bf16"]  # [total_kv, 1, 576]
        q_3d = q.view(bs, NUM_HEADS, QK_HEAD_DIM)  # [bs, 16, 576]
        kv_per_batch = kv_bf16.view(bs, kvseqlen, QK_HEAD_DIM)  # [bs, kvseqlen, 576]
        scores = torch.matmul(q_3d, kv_per_batch.transpose(1, 2))  # [bs, 16, kvseqlen]
        scores.mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1, dtype=torch.float32).to(torch.bfloat16)
        v_per_batch = kv_per_batch[:, :, :V_HEAD_DIM]  # [bs, kvseqlen, 512]
        out = torch.matmul(weights, v_per_batch)  # [bs, 16, 512]
        return out.view(bs * qseqlen, NUM_HEADS, V_HEAD_DIM)

    # ── Regime 2+3: aiter direct ASM dispatch ──
    kv_buffer_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    num_kv_splits = _choose_num_kv_splits(total_kv)
    kv_4d = kv_buffer_fp8.view(kv_buffer_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _get_cached_metadata(
        bs, qseqlen, kvseqlen,
        q_fp8.dtype, kv_buffer_fp8.dtype,
        qo_indptr, kv_indptr, num_kv_splits,
    )

    output = meta["output"]
    logits = meta["logits"]
    attn_lse = meta["attn_lse"]

    # Stage 1: ASM attention kernel
    mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d, qo_indptr, kv_indptr,
        meta["kv_indices"], meta["kv_last_page_len"],
        None,  # num_kv_splits_indptr
        meta["work_meta_data"], meta["work_indptr"], meta["work_info_set"],
        qseqlen, PAGE_SIZE, NUM_KV_HEADS, SM_SCALE,
        logits, attn_lse, output,
        q_scale, kv_scale,
    )

    # Stage 2: reduce
    mla_reduce_v1(
        logits, attn_lse,
        meta["reduce_indptr"], meta["reduce_final_map"], meta["reduce_partial_map"],
        qseqlen, output, None,
    )

    return output
