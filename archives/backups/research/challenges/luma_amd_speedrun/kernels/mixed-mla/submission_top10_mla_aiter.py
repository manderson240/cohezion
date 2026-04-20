import os

import torch
from task import input_t, output_t


# ─── TOP 10 MLA: ZERO-ALLOCATION AITER TUNING ──────────────────────────────
# All memory is pre-allocated at the module level to avoid stream noise.
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["AITER_KSPLIT"] = "8"
os.environ["AITER_BLOCK_M"] = "32"

_out_buffer = None


def custom_kernel(data: input_t) -> output_t:
    global _out_buffer
    q, kd, qi, ki, cfg = data
    bs, sl, nh = cfg["batch_size"], cfg["kv_seq_len"], cfg["num_heads"]

    # Pre-allocate output buffer once
    if _out_buffer is None or _out_buffer.shape[0] != bs:
        _out_buffer = torch.empty((bs, nh, 512), dtype=torch.bfloat16, device="cuda")

    from aiter.mla import mla_decode_fwd

    kf, ks = kd["fp8"]

    # Ensure synchronization before/after to force default stream usage
    torch.cuda.synchronize()

    res = mla_decode_fwd(
        q,
        kf,
        _out_buffer,
        qi,
        ki,
        page_size=1,
        nhead_kv=1,
        sm_scale=1.0 / (576**0.5),
        q_scale=None,
        kv_scale=ks,
        num_kv_splits=8,
        intra_batch_mode=True,
    )

    torch.cuda.synchronize()
    return res
