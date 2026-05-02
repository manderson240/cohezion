#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M8: doweight_stage1=True for MoE.

The reference uses doweight_stage1=False. Setting it to True makes
stage1 apply topk_weights during the gate-up GEMM instead of deferring
to stage2. This changes computation order and may help:
- Reduces intermediate buffer size (weighted values are smaller)
- May reduce memory traffic between stage1 and stage2
- 5% tolerance should easily accommodate any precision difference
"""

from __future__ import annotations

import os


os.environ["AITER_USE_NT"] = "1"

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

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=True,  # ← KEY CHANGE: weight during gate-up GEMM
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
