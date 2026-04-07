#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Probe sorting module to use ck_moe_stage1/stage2 directly."""

from __future__ import annotations
import os
import inspect
os.environ["AITER_USE_NT"] = "1"

import torch
import aiter
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]

    # Try to read fused_moe source for sorting logic
    try:
        src = inspect.getsource(fused_moe)
        # Find the sorting section
        lines = src.split('\n')
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in ['sort', 'moe_sorting', 'topk_ids', 'expert_ids', 'ck_moe']):
                start = max(0, i-1)
                end = min(len(lines), i+2)
                for j in range(start, end):
                    print(f"L{j}: {lines[j]}")
                print("---")
    except Exception as e:
        print(f"[PROBE] Cannot get fused_moe source: {e}")

    # Fallback
    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
    )
