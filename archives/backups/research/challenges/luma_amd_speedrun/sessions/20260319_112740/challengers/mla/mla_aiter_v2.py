"""
MLA AITER Max-Tuned — V2 with hidden env var discovery

Probe for undocumented AITER MLA environment variables and kernel paths.
This variant explores the hypothesis that the leader achieves 4.3µs through
undocumented env vars or hidden kernel dispatch paths.

Target: <10µs (breakthrough)
"""

import inspect
import os

import torch
from aiter import get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


# ─── Environment Variables to Explore ────────────────────────────────────────
# Known vars (from V1 plan)
os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_GFX950_EXPL_SCHED"] = "1"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["AITER_KSPLIT"] = "32"

# Additional vars to try (discovered through source inspection)
# These are set but may not all take effect — probe for actual behavior

# ─── MLA Configuration ────────────────────────────────────────────────────────
V_HEAD_DIM = 512
QK_HEAD_DIM = 576
NUM_KV_HEADS = 1
PAGE_SIZE = 1
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)


def probe_aiter_mla_ops():
    """Probe for hidden MLA ops in torch.ops.aiter."""
    hidden_ops = []
    if hasattr(torch.ops, "aiter"):
        for name in dir(torch.ops.aiter):
            if "mla" in name.lower() or "attn" in name.lower():
                hidden_ops.append(name)
    return hidden_ops


def probe_mla_source():
    """Probe mla_decode_fwd source for hidden env vars or code paths."""
    try:
        source = inspect.getsource(mla_decode_fwd)
        # Look for env var patterns
        import re

        env_patterns = re.findall(r"os\.environ\[([^\]]+)\]", source)
        return env_patterns
    except:
        return []


def custom_kernel(data: input_t) -> output_t:
    """
    MLA with env var exploration + max AITER tuning.

    This variant:
    1. Probes for hidden ops at startup
    2. Uses max-tuned AITER configuration
    3. Falls back to best-known configuration

    Expected: 20-30µs (if AITER is well-tuned)
    Breakthrough requires: finding hidden env var or kernel path
    """
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]
    total_q = q.shape[0]

    # Use FP8 KV (fastest path)
    kv_fp8, kv_scale = kv_data["fp8"]

    # Probe for hidden ops
    hidden_ops = probe_aiter_mla_ops()
    if hidden_ops:
        print(f"Discovered hidden ops: {hidden_ops}")

    # Probe source for env vars
    env_vars = probe_mla_source()
    if env_vars:
        print(f"MLA source uses env vars: {env_vars}")

    # Prepare indptr
    qo_indptr_i32 = qo_indptr.to(torch.int32)
    kv_indptr_i32 = kv_indptr.to(torch.int32)
    kv_last_page_len = kv_indptr_i32[1:] - kv_indptr_i32[:-1]

    # Get metadata for persistent mode
    meta = get_mla_metadata_v1(
        bs,
        qseqlen,
        nheads,
        q.dtype,
        kv_fp8.dtype,
        qo_indptr_i32,
        kv_indptr_i32,
        kv_last_page_len,
        num_kv_splits=32,
    )

    # Allocate output
    out = torch.empty((total_q, nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    # Execute via AITER MLA
    mla_decode_fwd(
        q.view(-1, nheads, QK_HEAD_DIM),
        kv_fp8,
        out,
        qo_indptr_i32,
        kv_indptr_i32,
        kv_last_page_len,
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=32,
        intra_batch_mode=True,
        **meta,
    )

    return out


if __name__ == "__main__":
    print("MLA AITER V2 — Max tuning + hidden op discovery")
    print(f"Hidden ops found: {probe_aiter_mla_ops()}")
    print(f"Source env vars: {probe_mla_source()}")
