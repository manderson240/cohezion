"""MLA decode — persistent + env-var optimized for MI355X.

Combines three strategies:
1. Matmul path for small shapes (bs<=8 OR total_kv<=65536) — proven fast
2. mla_decode_fwd (high-level API) with persistent env vars — potentially faster
3. Fallback to two-stage ASM (our current best) if high-level fails

Key env vars:
- AITER_MLA_USE_PERSISTENT=1: Enable persistent kernel scheduling
- AITER_USE_NT=1: Non-transposed memory access
- AITER_BYPASS_TUNE_CONFIG=1: Skip CSV config lookup overhead
"""

import os

os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

import torch
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)
from task import input_t, output_t


NUM_HEADS = 16
NUM_KV_HEADS = 1
KV_LORA_RANK = 512
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# Aggressive regime boundaries — matmul is fastest for small shapes
MATMUL_MAX_BS = 8
MATMUL_MAX_TOTAL_KV = 65536
A16W8_THRESHOLD = 262144

# Try importing high-level mla_decode_fwd
_mla_fwd = None
_mla_fwd_failed = False
try:
    from aiter.mla import mla_decode_fwd

    _mla_fwd = mla_decode_fwd
except Exception:
    _mla_fwd_failed = True

# Metadata cache
_cache: dict = {}


def _choose_splits(total_kv: int) -> int:
    if total_kv <= 2048:
        return 1
    if total_kv <= 16384:
        return 4
    if total_kv <= 65536:
        return 8
    if total_kv <= 262144:
        return 16
    return 32


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


def _get_meta(bs, qsl, kvsl, qdt, kvdt, qo_ind, kv_ind, splits):
    key = (bs, qsl, kvsl, qdt, kvdt, splits)
    if key in _cache:
        return _cache[key]

    nq, nkv = NUM_HEADS, NUM_KV_HEADS
    kv_last = (kv_ind[1:] - kv_ind[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(
        bs,
        qsl,
        nq,
        qdt,
        kvdt,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=splits,
        intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    wm, wi, wis, ri, rfm, rpm = work
    get_mla_metadata_v1(
        qo_ind,
        kv_ind,
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
        dtype_q=qdt,
        dtype_kv=kvdt,
    )
    tq = bs * qsl
    tkv = int(kv_ind[-1].item())
    meta = {
        "wm": wm,
        "wi": wi,
        "wis": wis,
        "ri": ri,
        "rfm": rfm,
        "rpm": rpm,
        "kvi": torch.arange(tkv, dtype=torch.int32, device="cuda"),
        "kvl": kv_last,
        "logits": torch.empty((splits, tq, nq, V_HEAD_DIM), dtype=torch.float32, device="cuda"),
        "lse": torch.empty((splits, tq, nq), dtype=torch.float32, device="cuda"),
        "out": torch.empty((tq, nq, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"),
    }
    _cache[key] = meta
    return meta


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qsl = config["q_seq_len"]
    kvsl = config["kv_seq_len"]
    total_kv = bs * kvsl

    # ── Regime 1: matmul (aggressive boundary) ──
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv = kv_data["bf16"]
        q3 = q.view(bs, NUM_HEADS, QK_HEAD_DIM)
        kv_b = kv.view(bs, kvsl, QK_HEAD_DIM)
        scores = torch.matmul(q3, kv_b.transpose(1, 2)).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1)
        v_b = kv_b[:, :, :V_HEAD_DIM]
        return torch.matmul(weights, v_b).view(bs * qsl, NUM_HEADS, V_HEAD_DIM)

    # ── Regime 2: Try high-level mla_decode_fwd (with persistent) ──
    if _mla_fwd is not None:
        try:
            kv_fp8, kv_scale = kv_data["fp8"]
            out = torch.empty(
                (bs * qsl, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"
            )
            splits = _choose_splits(total_kv)
            result = _mla_fwd(
                q,
                kv_fp8,
                out,
                qo_indptr,
                kv_indptr,
                page_size=PAGE_SIZE,
                nhead_kv=NUM_KV_HEADS,
                sm_scale=SM_SCALE,
                q_scale=None,
                kv_scale=kv_scale,
                num_kv_splits=splits,
                intra_batch_mode=True,
            )
            if result is not None:
                return result
            return out
        except Exception:
            pass  # Fall through to two-stage ASM

    # ── Regime 3: Two-stage ASM (proven path) ──
    kv_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    splits = _choose_splits(total_kv)
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    m = _get_meta(bs, qsl, kvsl, q_fp8.dtype, kv_fp8.dtype, qo_indptr, kv_indptr, splits)

    mla_decode_stage1_asm_fwd(
        q_fp8.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        qo_indptr,
        kv_indptr,
        m["kvi"],
        m["kvl"],
        None,
        m["wm"],
        m["wi"],
        m["wis"],
        qsl,
        PAGE_SIZE,
        NUM_KV_HEADS,
        SM_SCALE,
        m["logits"],
        m["lse"],
        m["out"],
        q_scale,
        kv_scale,
    )
    mla_reduce_v1(
        m["logits"],
        m["lse"],
        m["ri"],
        m["rfm"],
        m["rpm"],
        qsl,
        m["out"],
        None,
    )
    return m["out"]
