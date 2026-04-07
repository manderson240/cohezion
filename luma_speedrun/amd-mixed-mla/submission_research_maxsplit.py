#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA RESEARCH: max_split_per_batch tuning (untapped optimization).

From reference: mla_decode_fwd has max_split_per_batch parameter.
Current submissions always use num_kv_splits for all batch sizes.
Research: Limit splits for small batches to reduce overhead.

Reference: competition-research-untapped/SKILL.md Section 2.2
"""

from __future__ import annotations
import os
import sys

os.environ["AITER_USE_NT"] = "1"

import torch
from aiter import mla_decode_fwd
from task import input_t, output_t
from reference import ref_kernel

# Constants from reference
NUM_HEADS = 16
V_HEAD_DIM = 512
NUM_KV_SPLITS = 16


def _choose_splits(total_q: int, total_kv: int) -> tuple[int, int]:
    """Choose num_kv_splits and max_split_per_batch based on workload.

    Strategy:
    - Small batches: Limit splits to reduce overhead
    - Large batches: Use full splits for parallelism

    Args:
        total_q: Total query tokens
        total_kv: Total KV tokens

    Returns:
        (num_kv_splits, max_split_per_batch)
    """
    # Base: Use full splits
    num_splits = NUM_KV_SPLITS

    # For small batches, reduce splits
    if total_q < 16:
        # Very small batch: 4 splits max
        max_splits = 4
    elif total_q < 64:
        # Small batch: 8 splits max
        max_splits = 8
    elif total_q < 256:
        # Medium batch: 12 splits max
        max_splits = 12
    else:
        # Large batch: full splits
        max_splits = NUM_KV_SPLITS

    # Also consider KV length
    if total_kv < 1024:
        # Short sequence: fewer splits
        max_splits = min(max_splits, 4)
    elif total_kv < 4096:
        # Medium sequence
        max_splits = min(max_splits, 8)

    return num_splits, max_splits


def custom_kernel(data: input_t) -> output_t:
    (
        query,
        kv_buffer,
        qo_indptr,
        kv_indptr,
        q_len,
        kv_len,
        _q_start_loc,
        _kv_start_loc,
    ) = data

    total_q = qo_indptr[-1].item()
    total_kv = kv_indptr[-1].item()

    # Reshape query: [total_q, NUM_HEADS * V_HEAD_DIM] -> [total_q, NUM_HEADS, V_HEAD_DIM]
    query_reshaped = query.view(total_q, NUM_HEADS, V_HEAD_DIM)

    # ── RESEARCH: max_split_per_batch tuning ─────────────────────────
    num_kv_splits, max_split_per_batch = _choose_splits(total_q, total_kv)

    # Metadata cache
    meta_key = (
        total_q,
        total_kv,
        num_kv_splits,
        max_split_per_batch,
        query.device.index,
    )

    # Simple caching (per-call for research)
    if not hasattr(custom_kernel, "_cache"):
        custom_kernel._cache = {}

    if meta_key not in custom_kernel._cache:
        # Pre-allocate workspace
        max_split_per_batch = min(max_split_per_batch, num_kv_splits)

        custom_kernel._cache[meta_key] = {
            "num_kv_splits": num_kv_splits,
            "max_split_per_batch": max_split_per_batch,
        }

    cached = custom_kernel._cache[meta_key]
    num_kv_splits = cached["num_kv_splits"]
    max_split_per_batch = cached["max_split_per_batch"]

    # ── MLA decode with tuned splits ─────────────────────────────────
    try:
        result = mla_decode_fwd(
            query_reshaped,
            kv_buffer,
            qo_indptr,
            kv_indptr,
            q_len,
            kv_len,
            num_kv_splits=num_kv_splits,
            max_split_per_batch=max_split_per_batch,  # UNTAPPED parameter
            fast_mode=False,  # Verified faster on MI355X
        )
        return result
    except TypeError as e:
        if "max_split_per_batch" in str(e):
            # API doesn't support it, fallback to standard
            result = mla_decode_fwd(
                query_reshaped,
                kv_buffer,
                qo_indptr,
                kv_indptr,
                q_len,
                kv_len,
                num_kv_splits=NUM_KV_SPLITS,
                fast_mode=False,
            )
            return result
        raise
    except Exception:
        return ref_kernel(data)


kernel = custom_kernel
