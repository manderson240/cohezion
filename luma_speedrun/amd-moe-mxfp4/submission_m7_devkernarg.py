#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M7: HIP_FORCE_DEV_KERNARG=1 on clean MoE baseline.

HIP_FORCE_DEV_KERNARG=1 forces device-side kernel argument passing,
saving ~6µs per kernel launch. fused_moe launches multiple kernels
(sorting + stage1 + stage2), so cumulative savings could be significant.

Clean baseline with AITER_USE_NT=1 (required for MoE).
"""

from __future__ import annotations
import os

os.environ["HIP_FORCE_DEV_KERNARG"] = "1"
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
