"""MLA using mla_decode_fwd (non-ASM) with MXFP4 KV.

The ASM kernel (mla_decode_stage1_asm_fwd) rejects MXFP4 KV with
head_size==KV.size(3) assertion. But mla_decode_fwd may still work
since it's a different code path.
"""

import os

import torch
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"

_c, _o = {}, {}


def custom_kernel(data: input_t) -> output_t:
    q, kd, qi, ki, cfg = data
    b, sl, nh = cfg["batch_size"], cfg["kv_seq_len"], cfg["num_heads"]

    # Use MXFP4 KV cache
    kf, ks = kd["mxfp4"]
    k4 = kf.view(kf.shape[0], 1, 1, 288)

    # Adaptive num_kv_splits per (bs, kvseqlen)
    key = f"{b}_{sl}_{nh}"
    splits_table = {
        "4_1024_32": 4,
        "4_8192_32": 16,
        "32_1024_16": 8,
        "32_8192_16": 32,
        "32_1024_32": 8,
        "32_8192_32": 32,
        "128_8192_16": 32,
    }
    ns = splits_table.get(key, 16)

    # Pre-allocate output
    ok = (b * nh, 512)
    if ok not in _o:
        _o[ok] = torch.empty((b, nh, 512), dtype=torch.bfloat16, device="cuda")
    ot = _o[ok]

    # Use mla_decode_fwd (non-ASM) — may accept MXFP4 where ASM doesn't
    return mla_decode_fwd(
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
