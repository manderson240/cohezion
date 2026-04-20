#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Try fmoe_g1u1_a16 (discovered on runner, untested)."""

from __future__ import annotations
import os

os.environ["AITER_USE_NT"] = "1"

import torch
import aiter
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


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

    # Try fmoe_g1u1_a16 (gate+up fused, a16 = bf16 activations)
    try:
        result = aiter.fmoe_g1u1_a16(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            topk_ids,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
        )
        return result
    except Exception as e:
        print(f"[fmoe_g1u1_a16] Failed: {e}")

    # Fallback to standard fused_moe
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
