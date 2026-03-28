"""
MXFP4 MoE — Phase 12b: doweight_stage1 + block_size_M tuning.

Combines two optimizations:
1. doweight_stage1=True: fuses topk weight into stage1 GEMM
2. block_size_M=32 for sparse shapes: reduces empty tiles

For E=257, bs=16: ~0.56 tokens/expert → extremely sparse, block_m=32 (or 16)
For E=257, bs=512: ~18 tokens/expert → moderate, block_m=32
For E=33, bs=512: ~140 tokens/expert → dense, auto-select
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

    block_m = None

    if estimated_m >= 50:
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif num_experts >= 200 and estimated_m < 10:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
        block_m = 32
    else:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
        block_m = 32

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=True,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        block_size_M=block_m,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
