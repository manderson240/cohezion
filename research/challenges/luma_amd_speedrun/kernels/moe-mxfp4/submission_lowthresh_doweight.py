"""
MXFP4 MoE — Phase 12g: Lower dense threshold to 30, shape-aware routing.

Key insight from benchmark shapes:
- E=33, bs=128: estimated_m=35, currently uses KSPLIT=2 (cktile).
  Lowering dense threshold from 50→30 lets this shape use CK CSV-tuned
  configs + doweight_stage1=True (fused weight mul saves ~1-3µs).
- E=33, bs=512: estimated_m=140, already dense → CK + doweight.
- E=257, all bs: estimated_m < 20, always sparse → cktile KSPLIT.

CRITICAL: doweight_stage1=True is ONLY safe with CK path (KSPLIT=0).
"""
import os
from task import input_t, output_t
from aiter.fused_moe import fused_moe
from aiter import ActivationType, QuantType


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

    num_experts = gate_up_weight_shuffled.shape[0]
    estimated_m = topk_ids.numel() // num_experts

    if estimated_m >= 30:
        # Dense/near-dense: CK path (CSV-tuned, KSPLIT=0) + doweight safe
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
        doweight = True
    elif num_experts >= 200 and estimated_m < 10:
        # Very sparse (E=257, small bs): cktile KSPLIT=4
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
        doweight = False
    else:
        # Moderate sparse: cktile KSPLIT=2
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
        doweight = False

    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids, expert_mask=None,
        activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
        doweight_stage1=doweight,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
    )
