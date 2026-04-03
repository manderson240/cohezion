"""MLA decode — API landscape probe for MI355X.

Tests multiple untested aiter attention APIs to find the fastest path:
1. pa_ps_fwd_asm — persistent paged attention ASM kernel
2. flash_attn_varlen_func — FlashAttention variable-length
3. fmha_v3_varlen_fwd — FlashMHA v3
4. mla_decode_fwd — high-level wrapper with persistent mode

Falls back to proven two-stage ASM if all fail.

MLA tolerance: rtol=0.1, atol=0.1 (very loose — allows aggressive quantization).
"""

import os
import sys

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
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

MATMUL_MAX_BS = 8
MATMUL_MAX_TOTAL_KV = 65536

# ── Lazy-load API functions ──
_apis: dict = {}
_api_errors: dict = {}


def _load_apis():
    """Discover available aiter attention APIs at first call."""
    if _apis:
        return
    import aiter

    for name in [
        "gen_pa_ps_fwd_asm",
        "pa_ps_fwd_asm",
        "flash_attn_varlen_func",
        "fmha_v3_varlen_fwd",
    ]:
        fn = getattr(aiter, name, None)
        if fn is not None:
            _apis[name] = fn

    # Also try aiter.mla module
    try:
        from aiter.mla import mla_decode_fwd

        _apis["mla_decode_fwd"] = mla_decode_fwd
    except Exception:
        pass

    # Report discoveries
    print(f"MLA_APIS_FOUND: {list(_apis.keys())}", file=sys.stderr)


def _quantize_fp8(t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    fp8 = (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE)
    return fp8, scale.to(torch.float32).reshape(1)


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


# Metadata cache
_cache: dict = {}


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


def _try_flash_varlen(q, kv_data, qo_indptr, kv_indptr, config) -> torch.Tensor | None:
    """Try flash_attn_varlen_func with padded V."""
    fn = _apis.get("flash_attn_varlen_func")
    if fn is None or "flash_attn_varlen_func" in _api_errors:
        return None

    bs = config["batch_size"]
    kvsl = config["kv_seq_len"]
    qsl = config["q_seq_len"]
    total_kv = bs * kvsl

    kv_bf16 = kv_data["bf16"]  # (total_kv, 1, 576)

    # Pad V from 512 to 576 dims
    V_padded = torch.zeros(total_kv, 1, QK_HEAD_DIM, dtype=kv_bf16.dtype, device="cuda")
    V_padded[:, :, :V_HEAD_DIM] = kv_bf16[:, :, :V_HEAD_DIM]

    try:
        out = fn(
            q,
            kv_bf16,
            V_padded,
            cu_seqlens_q=qo_indptr,
            cu_seqlens_kv=kv_indptr,
            max_seqlen_q=qsl,
            max_seqlen_kv=kvsl,
            dropout_p=0.0,
            softmax_scale=SM_SCALE,
            causal=False,
        )
        if isinstance(out, tuple):
            out = out[0]
        return out[:, :, :V_HEAD_DIM].contiguous()
    except Exception as e:
        _api_errors["flash_attn_varlen_func"] = str(e)[:200]
        print(f"flash_varlen: {str(e)[:200]}", file=sys.stderr)
        return None


def _try_mla_decode_fwd(q, kv_data, qo_indptr, kv_indptr, config) -> torch.Tensor | None:
    """Try high-level mla_decode_fwd with persistent mode."""
    fn = _apis.get("mla_decode_fwd")
    if fn is None or "mla_decode_fwd" in _api_errors:
        return None

    bs = config["batch_size"]
    qsl = config["q_seq_len"]
    kvsl = config["kv_seq_len"]
    total_kv = bs * kvsl
    splits = _choose_splits(total_kv)

    kv_fp8, kv_scale = kv_data["fp8"]
    out = torch.empty((bs * qsl, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    try:
        result = fn(
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
        return result if result is not None else out
    except Exception as e:
        _api_errors["mla_decode_fwd"] = str(e)[:200]
        print(f"mla_decode_fwd: {str(e)[:200]}", file=sys.stderr)
        return None


def _try_pa_ps(q, kv_data, qo_indptr, kv_indptr, config) -> torch.Tensor | None:
    """Try gen_pa_ps_fwd_asm — persistent paged attention ASM kernel."""
    fn = _apis.get("gen_pa_ps_fwd_asm") or _apis.get("pa_ps_fwd_asm")
    if fn is None:
        return None
    name = "gen_pa_ps_fwd_asm" if "gen_pa_ps_fwd_asm" in _apis else "pa_ps_fwd_asm"
    if name in _api_errors:
        return None

    bs = config["batch_size"]
    kvsl = config["kv_seq_len"]
    total_kv = bs * kvsl

    kv_bf16 = kv_data["bf16"]  # (total_kv, 1, 576)
    K = kv_bf16.squeeze(1)  # (total_kv, 576)
    V = kv_bf16[:, 0, :V_HEAD_DIM].contiguous()  # (total_kv, 512)
    kv_page_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    context_lens = torch.full((bs,), kvsl, dtype=torch.int32, device="cuda")

    try:
        out = fn(q, K, V, kv_indptr, kv_page_indices, context_lens, SM_SCALE)
        if isinstance(out, tuple):
            out = out[0]
        if out.shape[-1] == V_HEAD_DIM:
            return out.view(-1, NUM_HEADS, V_HEAD_DIM).to(torch.bfloat16)
        if out.shape[-1] == QK_HEAD_DIM:
            return (
                out[..., :V_HEAD_DIM]
                .contiguous()
                .view(-1, NUM_HEADS, V_HEAD_DIM)
                .to(torch.bfloat16)
            )
        print(f"{name}_shape: {out.shape}", file=sys.stderr)
        return None
    except Exception as e:
        _api_errors[name] = str(e)[:200]
        print(f"{name}: {str(e)[:200]}", file=sys.stderr)
        return None


def custom_kernel(data: input_t) -> output_t:
    _load_apis()
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qsl = config["q_seq_len"]
    kvsl = config["kv_seq_len"]
    total_kv = bs * kvsl

    # ── Regime 1: matmul for small shapes ──
    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv = kv_data["bf16"]
        q3 = q.view(bs, NUM_HEADS, QK_HEAD_DIM)
        kv_b = kv.view(bs, kvsl, QK_HEAD_DIM)
        scores = torch.matmul(q3, kv_b.transpose(1, 2)).mul_(SM_SCALE)
        weights = torch.softmax(scores, dim=-1)
        v_b = kv_b[:, :, :V_HEAD_DIM]
        return torch.matmul(weights, v_b).view(bs * qsl, NUM_HEADS, V_HEAD_DIM)

    # ── Regime 2: Try new APIs (ordered by expected performance) ──

    # Try high-level mla_decode_fwd first (has persistent mode)
    result = _try_mla_decode_fwd(q, kv_data, qo_indptr, kv_indptr, config)
    if result is not None:
        return result

    # Try persistent paged attention ASM
    result = _try_pa_ps(q, kv_data, qo_indptr, kv_indptr, config)
    if result is not None:
        return result

    # Try FlashAttention varlen
    result = _try_flash_varlen(q, kv_data, qo_indptr, kv_indptr, config)
    if result is not None:
        return result

    # ── Regime 3: Proven two-stage ASM fallback ──
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
