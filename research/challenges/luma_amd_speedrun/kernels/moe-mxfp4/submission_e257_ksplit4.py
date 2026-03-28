"""
MXFP4 MoE — Phase 13b: KSPLIT=4 for ALL E>=200 shapes.

Change from Phase 12j: removes estimated_m < 10 guard for E>=200.
This means E=257 bs=512 (est_m=16) gets KSPLIT=4 instead of KSPLIT=2.

Rationale: With 257 experts and est_m=16, split-K=4 creates
257*4=1028 independent work items for 304 CUs (~3.4 items/CU).
KSPLIT=2 only gives 514 items (~1.7 items/CU).
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

    if num_experts >= 200:
        # ALL E=257 shapes: cktile KSPLIT=4 (high expert count = sparse)
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
    elif estimated_m >= 50:
        # Dense (E=33, large bs): CK path (KSPLIT=0)
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    else:
        # Moderate (E=33, small/medium bs): cktile KSPLIT=2
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"

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
