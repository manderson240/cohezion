"""
MXFP4 MoE — Phase 12m: Force cktile for ALL shapes.

Hypothesis: CK path (CSV-tuned) isn't faster for dense shapes since
CSV has no tuned entries for our competition shapes. The cktile path
might be competitive even at estimated_m=124, and avoids the ~105s
CK JIT build for module_moe_ck2stages.

Routing:
- m < 5:    KSPLIT=4 (very sparse)
- 5 ≤ m < 20:  KSPLIT=2
- 20 ≤ m < 80:  KSPLIT=1 (no split-K overhead)
- m ≥ 80:   KSPLIT=1 (still cktile, not CK)

All: doweight_stage1=False, AITER_BYPASS_TUNE_CONFIG=1.
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

    # Force cktile for ALL shapes
    os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

    if estimated_m < 5:
        os.environ["AITER_KSPLIT"] = "4"
    elif estimated_m < 20:
        os.environ["AITER_KSPLIT"] = "2"
    else:
        os.environ["AITER_KSPLIT"] = "1"

    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids, expert_mask=None,
        activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
    )
