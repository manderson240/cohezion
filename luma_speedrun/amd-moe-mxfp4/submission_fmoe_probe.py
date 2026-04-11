#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Probe fmoe_g1u1_a16 + fmoe_g1u1_fp4 + try different quant_type options."""

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

    # Probe 1: Try fmoe_g1u1_a16
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
        print("[MOE] fmoe_g1u1_a16 succeeded!")
        return result
    except Exception as e:
        print(f"[MOE] fmoe_g1u1_a16 failed: {e}")

    # Probe 2: Try with hidden_pad/intermediate_pad
    try:
        result = aiter.fmoe_g1u1_a16(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            topk_ids,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )
        print("[MOE] fmoe_g1u1_a16 with pads succeeded!")
        return result
    except Exception as e:
        print(f"[MOE] fmoe_g1u1_a16 with pads failed: {e}")

    # Probe 3: List available fmoe variants
    for name in dir(aiter):
        if "fmoe" in name.lower() or "moe" in name.lower():
            print(f"[MOE] Found: aiter.{name}")

    # Probe 4: Try doweight_stage1=True (previously avoided)
    try:
        result = fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            topk_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=True,  # TRY THIS
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )
        print("[MOE] doweight_stage1=True succeeded!")
        return result
    except Exception as e:
        print(f"[MOE] doweight_stage1=True failed: {e}")

    # Fallback to standard
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
