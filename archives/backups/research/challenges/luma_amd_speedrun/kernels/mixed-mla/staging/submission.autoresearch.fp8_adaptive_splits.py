"""MLA FP8 KV with aggressive adaptive num_kv_splits + updated API.

FP8 is the only working KV format after the aiter MXFP4 regression.
Optimize by using higher num_kv_splits for large shapes to maximize
CU parallelism, and lower for small shapes to reduce overhead.
"""

import os

import torch
from task import input_t, output_t


os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

_c, _o, _f1, _f2 = {}, {}, None, None


def _ea():
    global _f1, _f2
    if _f1:
        return
    try:
        from aiter.mla import mla_decode_stage1_asm_fwd as f1
        from aiter.mla import mla_reduce_v1 as f2

        _f1, _f2 = f1, f2
    except (ImportError, AttributeError):
        import aiter as a

        _f1, _f2 = getattr(a, "mla_decode_stage1_asm_fwd", None), getattr(a, "mla_reduce_v1", None)


def _bm(b, q, n, qd, kd, qi, ki, ns):
    from aiter import get_mla_metadata_info_v1 as gi
    from aiter import get_mla_metadata_v1 as gv

    i = gi(
        b, q, n, qd, kd, is_sparse=False, fast_mode=False, num_kv_splits=ns, intra_batch_mode=True
    )
    w = [torch.empty(s, dtype=t, device="cuda") for s, t in i]
    wm, wi, ws, ri, rf, rp = w
    kl = (ki[1:] - ki[:-1]).to(torch.int32)
    gv(
        qi,
        ki,
        kl,
        n,
        1,
        True,
        wm,
        ws,
        wi,
        ri,
        rf,
        rp,
        page_size=1,
        kv_granularity=16,
        max_seqlen_qo=q,
        uni_seqlen_qo=q,
        fast_mode=False,
        max_split_per_batch=ns,
        intra_batch_mode=True,
        dtype_q=qd,
        dtype_kv=kd,
    )
    return {"wm": wm, "wi": wi, "ws": ws, "ri": ri, "rf": rf, "rp": rp, "kl": kl, "ns": ns}


def custom_kernel(data: input_t) -> output_t:
    q, kd, qi, ki, cfg = data
    b, sl, nh = cfg["batch_size"], cfg["kv_seq_len"], cfg["num_heads"]
    _ea()

    # TP-aware, shape-aware cache key
    key = f"{b}_{sl}_{nh}"
    if key not in _c:
        # Aggressive adaptive splits table for FP8
        # FP8 has 2x bandwidth vs MXFP4, so we need MORE splits to hide latency
        splits_table = {
            "4_1024_32": 8,  # Small batch, short seq
            "4_8192_32": 32,  # Small batch, long seq — need parallelism
            "32_1024_16": 16,  # Medium batch, short seq (tp=8)
            "32_8192_16": 48,  # Medium batch, long seq (tp=8)
            "32_1024_32": 16,  # Medium batch, short seq (tp=4)
            "32_8192_32": 48,  # Medium batch, long seq (tp=4)
            "128_8192_16": 48,  # Large batch, long seq (tp=8)
        }
        ns = splits_table.get(key, 32)
        # FP8 KV: dtype is float8_e4m3fnuz
        _c[key] = _bm(b, 1, nh, torch.bfloat16, torch.float8_e4m3fnuz, qi, ki, ns)

    m = _c[key]
    ok = (b * nh, 512)
    if ok not in _o:
        _o[ok] = torch.empty((b, nh, 512), dtype=torch.bfloat16, device="cuda")
    ot = _o[ok]
    ns = m["ns"]
    buf_ns = max(ns, 16)

    # FP8 KV path
    kf, ks = kd["fp8"]
    k4 = kf.view(kf.shape[0], 1, 1, 576)  # FP8: full 576 dims, satisfies head_size check

    if _f1 and _f2:
        sd = torch.empty((b, buf_ns, nh, 520), dtype=torch.float32, device="cuda")
        sl_ = torch.empty((b, buf_ns, nh), dtype=torch.float32, device="cuda")
        _f1(
            q.view(b, nh, 576),
            k4,
            qi,
            ki,
            torch.arange(b * sl, dtype=torch.int32, device="cuda"),
            m["kl"],
            None,
            m["wm"],
            m["wi"],
            m["ws"],
            1,
            1,
            1,
            1.0 / (576**0.5),
            sd,
            sl_,
            ot,
            q_scale=None,
            kv_scale=ks,
        )
        _f2(sd, sl_, m["ri"], m["rf"], m["rp"], 1, ot)
        return ot

    from aiter.mla import mla_decode_fwd as mf

    return mf(
        q,
        k4,
        ot,
        qi,
        ki,
        page_size=1,
        nhead_kv=1,
        sm_scale=1.0 / (576**0.5),
        q_scale=None,
        kv_scale=ks,
        num_kv_splits=ns,
        intra_batch_mode=True,
    )
