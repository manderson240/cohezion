"""MLA — Batched matmul path for all sizes."""

import torch
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_decode_stage1_asm_fwd,
    mla_reduce_v1,
)


NUM_HEADS, NUM_KV_HEADS = 16, 1
KV_LORA_RANK, QK_HEAD_DIM, V_HEAD_DIM = 512, 576, 512
SM_SCALE, PAGE_SIZE = 1.0 / (QK_HEAD_DIM**0.5), 1
FP8_DTYPE = aiter_dtypes.fp8
MATMUL_MAX_BS, MATMUL_MAX_TOTAL_KV = 32, 262144
_cache = {}


def _quantize_fp8(t):
    finfo = torch.finfo(FP8_DTYPE)
    amax = t.abs().amax().clamp(min=1e-12)
    scale = amax / finfo.max
    return (t / scale).clamp(min=finfo.min, max=finfo.max).to(FP8_DTYPE), scale.to(
        torch.float32
    ).reshape(1)


def custom_kernel(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs, qsl, kvsl = config["batch_size"], config["q_seq_len"], config["kv_seq_len"]
    total_q, total_kv = bs * qsl, bs * kvsl

    if bs <= MATMUL_MAX_BS or total_kv <= MATMUL_MAX_TOTAL_KV:
        kv = kv_data["bf16"]
        q3, kv_b = q.view(bs, NUM_HEADS, QK_HEAD_DIM), kv.view(bs, kvsl, QK_HEAD_DIM)
        scores = torch.bmm(q3, kv_b.transpose(1, 2)) * SM_SCALE
        weights = torch.softmax(scores, dim=-1, dtype=torch.float32).to(torch.bfloat16)
        return torch.bmm(weights, kv_b[:, :, :V_HEAD_DIM]).view(total_q, NUM_HEADS, V_HEAD_DIM)

    kv_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)
    splits = 1 if total_kv <= 2048 else 4 if total_kv <= 16384 else 8 if total_kv <= 131072 else 16
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    key = (bs, qsl, kvsl, q_fp8.dtype, kv_fp8.dtype, splits)
    if key not in _cache:
        nq, nkv = NUM_HEADS, NUM_KV_HEADS
        kv_last = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
        info = get_mla_metadata_info_v1(
            bs,
            qsl,
            nq,
            q_fp8.dtype,
            kv_fp8.dtype,
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
            dtype_q=q_fp8.dtype,
            dtype_kv=kv_fp8.dtype,
        )
        tq, tkv = bs * qsl, int(kv_indptr[-1].item())
        _cache[key] = {
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
    m = _cache[key]

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
    mla_reduce_v1(m["logits"], m["lse"], m["ri"], m["rfm"], m["rpm"], qsl, m["out"], None)
    return m["out"]
