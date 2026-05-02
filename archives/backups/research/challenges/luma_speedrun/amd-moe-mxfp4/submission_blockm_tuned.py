#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Shape-aware block_m tuning based on aiter's internal dispatch.

From benchmark logs, aiter internally selects:
  - block_m=32 for estimated_m < 10 (sparse)
  - block_m=64 for estimated_m 10-100
  - block_m=128 for estimated_m > 100

The ksplit is INTERNALLY computed by aiter (env var IGNORED).
What we CAN control: the entry point parameters that affect
kernel selection.

Key insight from logs: aiter uses DIFFERENT kernel names based on shape.
For the 256-expert shapes, it uses pre-tuned CK kernels
(moe_ck2stages_gemm1_256x32x128x128 and _64x32x32x128).
For the 32-expert shapes, it falls back to "default" (cktile dispatch).

The pre-tuned 256-expert kernels are FASTER. The 32-expert default
kernels could be improved.

Strategy: Just use vanilla fused_moe with USE_NT=1 (confirmed working)
and let aiter's internal dispatch handle everything.
"""

from __future__ import annotations

import os


# Non-temporal memory hints (proven 10% improvement from vault)
os.environ["AITER_USE_NT"] = "1"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Pre-allocate output cache
_out_cache: dict[tuple, torch.Tensor] = {}


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

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
