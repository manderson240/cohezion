import os

import torch
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


# ─── THE ULTIMATE PERSISTENT MLA SPRINT (AITER NATIVE) ─────────────────────
# This configuration leverages the hidden CDNA 4 persistent logic in AITER.
os.environ["VLLM_ROCM_USE_AITER"] = "1"
os.environ["VLLM_ROCM_USE_AITER_MLA"] = "1"
os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_GFX950_EXPL_SCHED"] = "1"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["AITER_KSPLIT"] = "16"  # Maximum parallelism for the decode sweep


def custom_kernel(data: input_t) -> output_t:
    q, kd, qi, ki, cfg = data
    bs, sl, nh = cfg["batch_size"], cfg["kv_seq_len"], cfg["num_heads"]

    # Pre-allocate output buffer
    out = torch.empty((bs, nh, 512), dtype=torch.bfloat16, device="cuda")

    # We use the provided fp8 buffer which maps to the a8w8 ASM kernel
    kf, ks = kd["fp8"]

    # Execute via the high-level wrapper, but now backed by persistent kernels
    return mla_decode_fwd(
        q,
        kf,
        out,
        qi,
        ki,
        page_size=1,
        nhead_kv=1,
        sm_scale=1.0 / (576**0.5),
        q_scale=None,
        kv_scale=ks,
        num_kv_splits=16,  # Match AITER_KSPLIT
        intra_batch_mode=True,
    )
