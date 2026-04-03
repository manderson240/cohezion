"""MLA decode — matches official reference API for MI355X.

Uses the EXACT same mla_decode_fwd API as the official reference kernel,
with optimizations:
1. Matmul path for small shapes (faster than kernel dispatch)
2. Persistent env vars for larger shapes
3. Dynamic num_heads from config (handles tp=4 and tp=8)
4. Adaptive num_kv_splits based on total_kv

Key fix: uses config["num_heads"] instead of hardcoded 16 (handles tp=4 → 32 heads).
"""

import os

os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

import torch
from aiter import dtypes as aiter_dtypes
from aiter import get_mla_metadata_info_v1, get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t

NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

MATMUL_MAX_BS = 8
MATMUL_MAX_TOTAL_KV = 65536

_meta_cache: dict = {}


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _choose_splits(total_kv: int) -> int:
    """Match reference: use 32 splits for large KV, fewer for small."""
    if total_kv <= 2048:
        return 4
    if total_kv <= 16384:
        return 8
    if total_kv <= 65536:
        return 16
    return 32


def _build_meta(bs, qsl, nq, q_dtype, kv_dtype, qo_indptr, kv_indptr, splits):
    """Build persistent-mode metadata buffers (cached)."""
    key = (bs, qsl, nq, q_dtype, kv_dtype, splits)
    if key in _meta_cache:
        return _meta_cache[key]

    nkv = NUM_KV_HEADS
    kv_last = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)

    info = get_mla_metadata_info_v1(
        bs,
        qsl,
        nq,
        q_dtype,
        kv_dtype,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=splits,
        intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    wm, wi, wis, ri, rfm, rpm = work

    get_mla_metadata_v1(
        qo_indptr,
        kv_indptr,
        kv_last,
        nq // nkv,
        nkv,
        True,
        wm,
        wis,
        wi,
        ri,
        rfm,
        rpm,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qsl,
        uni_seqlen_qo=qsl,
        fast_mode=False,
        max_split_per_batch=splits,
        intra_batch_mode=True,
        dtype_q=q_dtype,
        dtype_kv=kv_dtype,
    )

    total_kv_len = int(kv_indptr[-1].item())
    meta = {
        "work_meta_data": wm,
        "work_indptr": wi,
        "work_info_set": wis,
        "reduce_indptr": ri,
        "reduce_final_map": rfm,
        "reduce_partial_map": rpm,
        "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
        "kv_last": kv_last,
    }
    _meta_cache[key] = meta
    return meta


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    nq = config["num_heads"]  # Dynamic! 16 for tp=8, 32 for tp=4
    qsl = config["q_seq_len"]
    kvsl = config["kv_seq_len"]
    total_kv = bs * kvsl

    # ── Regime 1: matmul for small shapes ──
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv = kv_data["bf16"]
        q3 = q.view(bs, nq, QK_HEAD_DIM)
        kv_b = kv.view(bs, kvsl, QK_HEAD_DIM)
        scores = torch.matmul(q3, kv_b.transpose(1, 2)).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1)
        v_b = kv_b[:, :, :V_HEAD_DIM]
        return torch.matmul(weights, v_b).view(bs * qsl, nq, V_HEAD_DIM)

    # ── Regime 2: mla_decode_fwd with persistent mode (matches reference API) ──
    kv_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    splits = _choose_splits(total_kv)

    # Reshape KV to 4D: (total_kv, page_size, nhead_kv, dim)
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _build_meta(bs, qsl, nq, q_fp8.dtype, kv_fp8.dtype, qo_indptr, kv_indptr, splits)

    o = torch.empty((q.shape[0], nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    mla_decode_fwd(
        q_fp8.view(-1, nq, QK_HEAD_DIM),
        kv_4d,
        o,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last"],
        qsl,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=splits,
        q_scale=q_scale,
        kv_scale=kv_scale,
        intra_batch_mode=True,
        work_meta_data=meta["work_meta_data"],
        work_indptr=meta["work_indptr"],
        work_info_set=meta["work_info_set"],
        reduce_indptr=meta["reduce_indptr"],
        reduce_final_map=meta["reduce_final_map"],
        reduce_partial_map=meta["reduce_partial_map"],
    )
    return o
