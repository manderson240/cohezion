"""
MXFP4 MoE — Phase 13: block_size_M override for moderate-sparse shapes.

Hypothesis: For bs=512,257E (est_m=17), the heuristic picks block_m=64
because total_tokens=4608 > 2048. But with est_m=17, tiles are mostly
empty. block_m=32 would create more tiles with better utilization.

Strategy:
  - estimated_m >= 50: CK path (no override)
  - num_experts >= 200 AND estimated_m < 10: BYPASS+K4, block_m=32
  - estimated_m < 50 AND estimated_m >= 10: BYPASS+K2, block_m=32
  - estimated_m < 10 (small expert count): BYPASS+K2, block_m=32
"""
import os
from task import input_t, output_t
from aiter.fused_moe import fused_moe
from aiter import ActivationType, QuantType


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

    num_experts = gate_up_weight_shuffled.shape[0]
    estimated_m = topk_ids.numel() // num_experts

    block_m = None  # default: let aiter auto-select

    if estimated_m >= 50:
        # Dense: CK MXFP4-optimized path
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif num_experts >= 200 and estimated_m < 10:
        # Large expert count, very sparse: KSPLIT=4
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
        block_m = 32
    else:
        # Moderate sparse: KSPLIT=2
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
        block_m = 32  # Override heuristic block_m=64 for sparse shapes

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
        block_size_M=block_m,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
