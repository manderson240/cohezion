#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Probe ranked shapes."""

from __future__ import annotations
import os

os.environ["AITER_USE_NT"] = "1"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

_call_count = 0


def custom_kernel(data: input_t) -> output_t:
    global _call_count
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

    _call_count += 1
    print(
        f"[SHAPE] call={_call_count} bs={config.get('bs')} "
        f"d_hidden={config.get('d_hidden')} d_expert={config.get('d_expert')} "
        f"n_routed={config.get('n_routed_experts')} n_shared={config.get('n_shared_experts')} "
        f"topk={config.get('nexpertspertoken')} "
        f"d_hidden_pad={config.get('d_hidden_pad')} d_expert_pad={config.get('d_expert_pad')}"
    )

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
