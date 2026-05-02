#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""Compound v1: Buffer pre-allocation + direct dispatch (no torch.ops overhead).

The baseline calls:
  fused_moe() -> fused_moe_() [torch.ops dispatch] -> moe_sorting() [5 allocs] -> fused_moe_2stages()

This submission replaces the entire chain with:
  custom_kernel() -> _fast_moe() [direct Python] -> moe_sorting_fwd [pre-allocated] -> fused_moe_2stages()

Key optimizations:
  1. Bypass torch.ops.aiter dispatch layer (fused_moe_ is registered as a custom op)
  2. Pre-allocate ALL 5 sorting buffers per (M, topk, E, model_dim, block_m) shape key
  3. Cache shape metadata (get_2stage_cfgs is already LRU-cached; we also cache derived values)
  4. AITER_USE_NT=1 (non-temporal loads, confirmed working)
  5. Shape-aware constants (hidden_pad, intermediate_pad) cached via lru_cache

The moe_sorting() call allocates 5 tensors on EVERY invocation:
  sorted_ids [max_tokens_padded], sorted_weights [max_tokens_padded],
  sorted_expert_ids [max_m_blocks], num_valid_ids [2], moe_buf [M, model_dim]
Pre-allocating eliminates this allocation overhead entirely on the hot path.
"""

from __future__ import annotations

import os


os.environ["AITER_USE_NT"] = "1"

import functools

import aiter
import torch
from aiter import ActivationType, QuantType, dtypes
from aiter.fused_moe import (
    fused_moe_2stages,
    get_2stage_cfgs,
    get_inter_dim,
    get_padded_M,
)
from task import input_t, output_t


# --------------------------------------------------------------------------
# Per-shape sort buffer cache
# Keyed by (M, topk, global_E, model_dim, block_m, dtype, device_str)
# --------------------------------------------------------------------------
_SORT_BUF_CACHE: dict = {}


def _ensure_sort_bufs(
    M: int,
    topk: int,
    global_E: int,
    model_dim: int,
    block_m: int,
    dtype: torch.dtype,
    device: torch.device,
):
    """Return pre-allocated sort buffers for this shape, allocating once."""
    key = (M, topk, global_E, model_dim, block_m, dtype, device.index)
    cached = _SORT_BUF_CACHE.get(key)
    if cached is not None:
        return cached

    max_tokens_padded = int(M * topk + global_E * block_m - topk)
    max_m_blocks = int((max_tokens_padded + block_m - 1) // block_m)

    bufs = (
        torch.empty(max_tokens_padded, dtype=dtypes.i32, device=device),
        torch.empty(max_tokens_padded, dtype=dtypes.fp32, device=device),
        torch.empty(max_m_blocks, dtype=dtypes.i32, device=device),
        torch.empty(2, dtype=dtypes.i32, device=device),
        torch.empty((M, model_dim), dtype=dtype, device=device),
    )
    _SORT_BUF_CACHE[key] = bufs
    return bufs


# --------------------------------------------------------------------------
# Cached per-shape constants (trivial dict lookups but called every iteration)
# --------------------------------------------------------------------------
@functools.lru_cache(maxsize=64)
def _shape_constants(
    d_hidden_pad: int,
    d_hidden: int,
    d_expert_pad: int,
    d_expert: int,
) -> tuple[int, int]:
    return (d_hidden_pad - d_hidden, d_expert_pad - d_expert)


# --------------------------------------------------------------------------
# Cached metadata + derived values per unique shape
# --------------------------------------------------------------------------
@functools.lru_cache(maxsize=256)
def _get_shape_meta(
    M: int,
    E: int,
    topk: int,
    model_dim: int,
    inter_dim: int,
    dtype,
    q_dtype_a,
    q_dtype_w,
    quant_type,
    activation,
    hidden_pad: int,
    intermediate_pad: int,
    is_g1u1: bool,
    is_shuffled: bool,
):
    """Return (metadata, block_m) for this shape; fully cached after first call."""
    meta = get_2stage_cfgs(
        get_padded_M(M),
        model_dim,
        inter_dim,
        E,
        topk,
        dtype,
        q_dtype_a,
        q_dtype_w,
        quant_type,
        is_g1u1,
        activation,
        False,  # doweight_stage1 = False (always)
        hidden_pad,
        intermediate_pad,
        is_shuffled,
    )
    return meta, int(meta.block_m)


# --------------------------------------------------------------------------
# Fast MoE forward: replaces fused_moe() + fused_moe_() + torch.ops dispatch
# --------------------------------------------------------------------------
def _fast_moe(
    hidden_states: torch.Tensor,
    w1: torch.Tensor,
    w2: torch.Tensor,
    topk_weight: torch.Tensor,
    topk_ids: torch.Tensor,
    w1_scale: torch.Tensor,
    w2_scale: torch.Tensor,
    hidden_pad: int,
    intermediate_pad: int,
) -> torch.Tensor:
    M, topk = topk_ids.shape
    E, model_dim, inter_dim = get_inter_dim(w1.shape, w2.shape)

    # For MXFP4 per_1x32 + Silu + gfx950: q_dtype_a = fp4x2
    q_dtype_w = w1.dtype
    q_dtype_a = dtypes.fp4x2
    quant_type = QuantType.per_1x32
    activation = ActivationType.Silu
    dtype = hidden_states.dtype  # bf16

    # isG1U1: True when inter_dim != w1.shape[1] (gate+up fused)
    is_g1u1 = inter_dim != w1.shape[1]
    is_shuffled = getattr(w1, "is_shuffled", False)

    # get_2stage_cfgs is already @functools.lru_cache; _get_shape_meta adds one
    # more cache layer that avoids the quant_remap + gfx950 branch checks.
    meta, block_m = _get_shape_meta(
        M,
        E,
        topk,
        model_dim,
        inter_dim,
        dtype,
        q_dtype_a,
        q_dtype_w,
        quant_type,
        activation,
        hidden_pad,
        intermediate_pad,
        is_g1u1,
        is_shuffled,
    )

    device = topk_ids.device

    # Use pre-allocated sort buffers (bypasses 5x torch.empty per call)
    sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids, moe_buf = _ensure_sort_bufs(
        M, topk, E, model_dim, block_m, dtype, device
    )

    # Direct moe_sorting_fwd call (same as moe_sorting() but no tensor allocations)
    aiter.moe_sorting_fwd(
        topk_ids,
        topk_weight,
        sorted_ids,
        sorted_weights,
        sorted_expert_ids,
        num_valid_ids,
        moe_buf,
        E,  # global_E (no expert_mask, so global_E == E)
        block_m,
        None,  # local_expert_mask
        None,  # num_local_tokens
        0,  # dispatch_policy
    )

    # fused_moe_2stages is pure Python (not wrapped in torch.ops)
    return fused_moe_2stages(
        hidden_states,
        w1,
        w2,
        topk,
        sorted_ids,
        sorted_weights,
        sorted_expert_ids,
        num_valid_ids,
        moe_buf,
        is_g1u1,
        block_m,
        activation=activation,
        quant_type=quant_type,
        doweight_stage1=False,
        q_dtype_a=q_dtype_a,
        q_dtype_w=q_dtype_w,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        a1_scale=None,
        a2_scale=None,
        num_local_tokens=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
        bias1=None,
        bias2=None,
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states,
        gate_up_weight,
        down_weight,
        gate_up_weight_scale,
        down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    hidden_pad, intermediate_pad = _shape_constants(
        config["d_hidden_pad"],
        config["d_hidden"],
        config["d_expert_pad"],
        config["d_expert"],
    )

    return _fast_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        hidden_pad,
        intermediate_pad,
    )
