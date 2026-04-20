import os

import torch
from aiter import dtypes as dt
from task import input_t, output_t


os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
# Removed AITER_USE_NT — MLA uses ASM kernels, not CK GEMM; NT may not help
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

_splits_table = {"4_1024": 4, "4_8192": 16, "32_1024": 8, "32_8192": 32, "128_8192": 32}
_default_splits = 16
_fast_mode = False
_kv_gran = 16
_kv_format = "fp8"
_c, _o, _f1, _f2 = {}, {}, None, None


def _ea():
    global _f1, _f2
    if _f1:
        return
    try:
        from aiter.mla import mla_decode_stage1_asm_fwd as f1
        from aiter.mla import mla_reduce_v1 as f2

        _f1, _f2 = f1, f2
    except:
        import aiter as a

        _f1, _f2 = getattr(a, "mla_decode_stage1_asm_fwd", None), getattr(a, "mla_reduce_v1", None)


def _bm(b, q, n, qd, kd, qi, ki, ns):
    from aiter import get_mla_metadata_info_v1 as gi
    from aiter import get_mla_metadata_v1 as gv

    i = gi(
        b,
        q,
        n,
        qd,
        kd,
        is_sparse=False,
        fast_mode=_fast_mode,
        num_kv_splits=ns,
        intra_batch_mode=True,
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
        kv_granularity=_kv_gran,
        max_seqlen_qo=q,
        uni_seqlen_qo=q,
        fast_mode=_fast_mode,
        max_split_per_batch=ns,
        intra_batch_mode=True,
        dtype_q=qd,
        dtype_kv=kd,
    )
    return {"wm": wm, "wi": wi, "ws": ws, "ri": ri, "rf": rf, "rp": rp, "kl": kl, "ns": ns}


def custom_kernel(data: input_t) -> output_t:
    q, kd, qi, ki, cfg = data
    b, sl, nh = cfg["batch_size"], cfg["kv_seq_len"], cfg["num_heads"]
    qs = q.shape[0] // b
    _ea()
    key = f"{b}_{sl}_{nh}_{qs}"
    if key not in _c:
        ns = _splits_table.get(f"{b}_{sl}_{nh}", _splits_table.get(f"{b}_{sl}", _default_splits))
        kv_dt = dt.fp4x2 if _kv_format == "mxfp4" else torch.float8_e4m3fnuz
        _c[key] = _bm(b, qs, nh, torch.bfloat16, kv_dt, qi, ki, ns)
    m = _c[key]
    ok = (b * nh, 512)
    if ok not in _o:
        _o[ok] = torch.empty((b, nh, 512), dtype=torch.bfloat16, device="cuda")
    ot = _o[ok]
    ns = m["ns"]
    buf_ns = max(ns, 16)
    if _kv_format == "mxfp4":
        kf, ks = kd["mxfp4"]
        k4 = kf.view(kf.shape[0], 1, 1, 288)
    else:
        kf, ks = kd["fp8"]
        k4 = kf.view(kf.shape[0], 1, 1, 576)
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
