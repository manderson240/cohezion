#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: dispatch_policy=1 + shape-aware KSPLIT.

Combines two GPU-level optimizations:
1. moe_sorting_dispatch_policy=1 (37% worst-case improvement on sorting)
2. Shape-aware KSPLIT: 0 for small K (d_expert<=512), default for large K
No Python-level overhead (no expert_mask computation).
"""

from __future__ import annotations

import os


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

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
    d_expert = config.get("d_expert", 0)

    # Shape-aware KSPLIT: no split for tiny K, default for large K
    if d_expert <= 512:
        os.environ["AITER_KSPLIT"] = "0"
    else:
        os.environ.pop("AITER_KSPLIT", None)

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
        moe_sorting_dispatch_policy=1,
    )
