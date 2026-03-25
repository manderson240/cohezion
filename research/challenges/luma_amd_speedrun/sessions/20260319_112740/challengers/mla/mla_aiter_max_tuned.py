"""
MLA AITER Max Tuned — AITER with maximum performance environment tuning.

This variant maximizes AITER's built-in MLA optimizations through environment
variables. It serves as a comparison baseline against custom MFMA kernels.

Target: <20µs with proper AITER tuning
Approach: Environment-driven optimization, no custom HIP code
"""

import os

import torch
from aiter import get_mla_metadata_v1
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


# ─── AITER ENVIRONMENT TUNING ───────────────────────────────────────────────
# Maximum performance environment variables for MLA on MI355X (gfx950)

# Persistent kernel mode — keeps KV working set in L2 cache
os.environ["AITER_MLA_USE_PERSISTENT"] = "1"

# Explicit scheduling for gfx950 — enables CDNA 3 schedule optimizations
os.environ["AITER_GFX950_EXPL_SCHED"] = "1"

# Use NVIDIA Tensor core path simulation (benefits AMD MFMA paths)
os.environ["AITER_USE_NT"] = "1"

# Bypass CSV tuning — use explicit config instead of search
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

# Maximum KV splits for decode — more parallelism
os.environ["AITER_KSPLIT"] = "32"

# Additional MLA optimizations
os.environ["VLLM_ROCM_USE_AITER"] = "1"
os.environ["VLLM_ROCM_USE_AITER_MLA"] = "1"

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
V_HEAD_DIM = 512
QK_HEAD_DIM = 576
NUM_KV_HEADS = 1
PAGE_SIZE = 1
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)


def custom_kernel(data: input_t) -> output_t:
    """
    AITER MLA with maximum environment tuning.

    This configuration achieved best AITER baseline in previous rounds.
    Use as comparison baseline for custom MFMA kernels.

    Expected: ~20-30µs depending on shape
    """
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]

    # Use FP8 KV cache (fastest path through AITER)
    kv_fp8, kv_scale = kv_data["fp8"]

    # Convert indptr to int32 (required by AITER)
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
        num_kv_splits=32,  # Maximum splits for decode parallelism
    )

    # Pre-allocate output
    total_q = q.shape[0]
    out = torch.empty((total_q, nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")

    # Execute via AITER MLA (backed by CDNA 3 MFMA kernels)
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
        intra_batch_mode=True,  # Enable intra-batch optimizations
        **meta,
    )

    return out


if __name__ == "__main__":
    print("MLA AITER Max Tuned — AITER with maximum env optimization")
    print("Target: <30µs (best AITER baseline)")
    print("Env vars: PERSISTENT=1, GFX950_EXPL_SCHED=1, KSPLIT=32")
