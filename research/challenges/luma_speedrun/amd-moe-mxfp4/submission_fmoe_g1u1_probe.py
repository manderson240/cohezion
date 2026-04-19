#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""MoE: Probe fmoe_g1u1 (non-a16 variant) and ck_moe_stage1 signatures."""

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

    # Probe fmoe_g1u1 signature
    try:
        sig = str(inspect.signature(aiter.fmoe_g1u1))
        print(f"[PROBE] fmoe_g1u1 sig: {sig[:500]}")
    except Exception as e:
        print(f"[PROBE] fmoe_g1u1 sig error: {e}")

    # Probe fmoe_g1u1_tkw1 signature
    try:
        sig = str(inspect.signature(aiter.fmoe_g1u1_tkw1))
        print(f"[PROBE] fmoe_g1u1_tkw1 sig: {sig[:500]}")
    except Exception as e:
        print(f"[PROBE] fmoe_g1u1_tkw1 sig error: {e}")

    # Probe ck_moe_stage1 signature
    try:
        sig = str(inspect.signature(aiter.ck_moe_stage1))
        print(f"[PROBE] ck_moe_stage1 sig: {sig[:500]}")
    except Exception as e:
        print(f"[PROBE] ck_moe_stage1 sig error: {e}")

    # Probe ck_moe_stage2 signature
    try:
        sig = str(inspect.signature(aiter.ck_moe_stage2))
        print(f"[PROBE] ck_moe_stage2 sig: {sig[:500]}")
    except Exception as e:
        print(f"[PROBE] ck_moe_stage2 sig error: {e}")

    # Try fmoe_fp8_blockscale_g1u1
    try:
        sig = str(inspect.signature(aiter.fmoe_fp8_blockscale_g1u1))
        print(f"[PROBE] fmoe_fp8_blockscale_g1u1 sig: {sig[:500]}")
    except Exception as e:
        print(f"[PROBE] fmoe_fp8_blockscale_g1u1 sig error: {e}")

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
