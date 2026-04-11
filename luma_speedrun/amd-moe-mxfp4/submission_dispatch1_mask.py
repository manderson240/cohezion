#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: dispatch_policy=1 + expert_mask for sparse dispatch.

Combines two optimizations:
1. moe_sorting_dispatch_policy=1 (37% worst-case improvement)
2. expert_mask to skip empty expert dispatches (10-15µs expected saving)
"""

from __future__ import annotations
import os

os.environ["AITER_USE_NT"] = "1"

import torch
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
    E_total = config["n_routed_experts"] + config.get("n_shared_experts", 0)

    # Compute expert mask: which experts have at least one token routed to them
    expert_counts = torch.bincount(topk_ids.flatten(), minlength=E_total)
    expert_mask = (expert_counts > 0).to(torch.int32)

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=expert_mask,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
        moe_sorting_dispatch_policy=1,
    )
