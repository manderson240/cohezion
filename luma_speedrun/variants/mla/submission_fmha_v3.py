"""MLA decode — FlashMHA V3 + SAGE MXFP4 probe for MI355X.

Tests the untested high-priority APIs discovered by research agent:
1. fmha_v3_varlen_fwd (priority 0.88) — latest FlashMHA V3, CDNA4-optimized
2. fav3_sage_attn_fwd — SAGE attention variant
3. fav3_sage_mxfp4 — MXFP4-native (could eliminate quant overhead entirely)

Falls back to proven mla_decode_fwd if all fail.

MLA tolerance: rtol=1e-2, atol=1e-2
"""

import os
import sys

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

# ── Lazy-load experimental APIs ──
_apis: dict = {}
_api_errors: set = set()
_apis_loaded = False


def _load_apis():
    global _apis_loaded
    if _apis_loaded:
        return
    _apis_loaded = True
    import aiter

    for name in [
        "fmha_v3_varlen_fwd",
        "fmha_varlen_fwd",
        "fav3_sage_attn_fwd",
        "fav3_sage_mxfp4",
        "flash_attn_varlen_func",
    ]:
        fn = getattr(aiter, name, None)
        if fn is not None:
            _apis[name] = fn

    print(f"MLA_V3_APIS: {list(_apis.keys())}", file=sys.stderr)


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


_meta_cache: dict = {}


def _build_meta(bs, qsl, nq, q_dtype, kv_dtype, qo_indptr, kv_indptr, splits):
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


def _try_fmha_v3(q, kv_data, qo_indptr, kv_indptr, config) -> torch.Tensor | None:
    """Try FlashMHA V3 variable-length."""
    fn = _apis.get("fmha_v3_varlen_fwd")
    if fn is None or "fmha_v3_varlen_fwd" in _api_errors:
        return None

    bs = config["batch_size"]
    nq = config["num_heads"]
    qsl = config["q_seq_len"]
    kvsl = config["kv_seq_len"]
    total_kv = bs * kvsl

    kv_bf16 = kv_data["bf16"]  # (total_kv, 1, 576)
    K = kv_bf16.expand(-1, nq, -1)  # broadcast kv_heads to q_heads
    V = kv_bf16[:, :, :V_HEAD_DIM].expand(-1, nq, -1)

    # Try multiple call patterns
    for attempt, kwargs in enumerate(
        [
            {
                "q": q,
                "k": K,
                "v": V,
                "cu_seqlens_q": qo_indptr,
                "cu_seqlens_k": kv_indptr,
                "max_seqlen_q": qsl,
                "max_seqlen_k": kvsl,
                "softmax_scale": SM_SCALE,
            },
            {
                "q": q,
                "k": kv_bf16,
                "v": kv_bf16[:, :, :V_HEAD_DIM],
                "cu_seqlens_q": qo_indptr,
                "cu_seqlens_k": kv_indptr,
                "max_seqlen_q": qsl,
                "max_seqlen_k": kvsl,
                "softmax_scale": SM_SCALE,
            },
        ]
    ):
        try:
            out = fn(**kwargs)
            if isinstance(out, tuple):
                out = out[0]
            if out.shape[-1] >= V_HEAD_DIM:
                return (
                    out[..., :V_HEAD_DIM].contiguous().view(-1, nq, V_HEAD_DIM).to(torch.bfloat16)
                )
        except Exception as e:
            print(f"fmha_v3_attempt{attempt}: {str(e)[:200]}", file=sys.stderr)

    _api_errors.add("fmha_v3_varlen_fwd")
    return None


def _try_sage_mxfp4(q, kv_data, config) -> torch.Tensor | None:
    """Try SAGE MXFP4-native attention (could skip quant entirely)."""
    fn = _apis.get("fav3_sage_mxfp4")
    if fn is None or "fav3_sage_mxfp4" in _api_errors:
        return None

    nq = config["num_heads"]

    if "mxfp4" not in kv_data:
        return None

    kv_fp4, kv_scale = kv_data["mxfp4"]
    try:
        out = fn(q, kv_fp4, kv_scale, softmax_scale=SM_SCALE)
        if isinstance(out, tuple):
            out = out[0]
        return out[..., :V_HEAD_DIM].contiguous().view(-1, nq, V_HEAD_DIM).to(torch.bfloat16)
    except Exception as e:
        print(f"sage_mxfp4: {str(e)[:200]}", file=sys.stderr)
        _api_errors.add("fav3_sage_mxfp4")
        return None


def custom_kernel(data: input_t) -> output_t:
    _load_apis()
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    nq = config["num_heads"]
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

    # ── Regime 2: Try experimental APIs ──

    # Try SAGE MXFP4 first (lowest quant overhead)
    result = _try_sage_mxfp4(q, kv_data, config)
    if result is not None:
        return result

    # Try FlashMHA V3
    result = _try_fmha_v3(q, kv_data, qo_indptr, kv_indptr, config)
    if result is not None:
        return result

    # ── Regime 3: Proven mla_decode_fwd ──
    kv_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    splits = 32  # Match reference default

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
        **{
            k: meta[k]
            for k in (
                "work_meta_data",
                "work_indptr",
                "work_info_set",
                "reduce_indptr",
                "reduce_final_map",
                "reduce_partial_map",
            )
        },
    )
    return o
