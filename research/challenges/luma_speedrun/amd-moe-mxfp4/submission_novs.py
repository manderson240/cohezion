#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Try the 'novs' (no vertical scaling) FP8 blockscale kernel.

DISCOVERY: Runner has fmoe_fp8_blockscale_g1u1_novs_subGU_256.co
This is a DIFFERENT GPU kernel than the standard fused_moe dispatch.
The 'novs' variant skips vertical scaling — potentially 10-20% faster.

Approach: Use fmoe_fp8_blockscale_g1u1 or fmoe_g1u1_a16 API if available.
"""

from __future__ import annotations
import os

os.environ["AITER_USE_NT"] = "1"

import torch
import aiter
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# Probe for alternative MoE APIs
_alt_moe = None
for api_name in ["fmoe_fp8_blockscale_g1u1", "fmoe_g1u1_a16", "asm_moe"]:
    fn = getattr(aiter, api_name, None)
    if fn is not None:
        _alt_moe = (api_name, fn)
        break


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

    # Try alternative API first
    if _alt_moe is not None:
        api_name, fn = _alt_moe
        try:
            if api_name == "fmoe_fp8_blockscale_g1u1":
                return fn(
                    hidden_states,
                    gate_up_weight_shuffled,
                    down_weight_shuffled,
                    topk_weights,
                    topk_ids,
                    w1_scale=gate_up_weight_scale_shuffled,
                    w2_scale=down_weight_scale_shuffled,
                )
            elif api_name == "fmoe_g1u1_a16":
                return fn(
                    hidden_states,
                    gate_up_weight_shuffled,
                    down_weight_shuffled,
                    topk_weights,
                    topk_ids,
                    w1_scale=gate_up_weight_scale_shuffled,
                    w2_scale=down_weight_scale_shuffled,
                )
        except Exception as e:
            print(f"[novs] alt API {api_name} failed: {e}")

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
