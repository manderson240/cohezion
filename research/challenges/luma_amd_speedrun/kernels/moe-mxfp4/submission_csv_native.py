"""
MXFP4 MoE — Phase 12h: Pure CSV-native + selective doweight.

Hypothesis: For DeepSeek benchmark shapes (E=257, d=7168), the
dsv3_fp4_tuned_fmoe.csv has dedicated CK configs. Bypassing the
tuned config (AITER_BYPASS_TUNE_CONFIG=1) forces cktile, which may
be suboptimal for shapes that have carefully tuned CK entries.

Strategy: NEVER bypass tune config. Let aiter use CSV-tuned CK path
for ALL shapes. Only enable doweight_stage1=True for shapes dense
enough to be on the CK path (estimated_m >= 30).

For very sparse shapes (estimated_m < 10), doweight_stage1 is risky
because if CSV has no entry, fallback to cktile + doweight = GPU fault.
So doweight=False for sparse shapes as safety net.

KSPLIT is ONLY set for sparse shapes where the CK path has no CSV
entry and would pick suboptimal defaults.
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

    # Always let CSV configs be available
    os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)

    if estimated_m >= 30:
        # Dense enough for CK path — doweight safe, no KSPLIT override
        os.environ.pop("AITER_KSPLIT", None)
        doweight = True
    elif num_experts >= 200:
        # Very sparse E=257: hint KSPLIT=4 but DON'T bypass CSV
        os.environ["AITER_KSPLIT"] = "4"
        doweight = False
    else:
        # Moderate: hint KSPLIT=2 but DON'T bypass CSV
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
