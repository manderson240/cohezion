"""
MXFP4 MoE — Phase 12d: doweight_stage1 + online tune for sparse shapes.

Combines:
1. doweight_stage1=True: fuses topk weight into stage1 GEMM (saves ~1-3us)
2. AITER_ONLINE_TUNE=1 for sparse shapes: runtime autotuning may find
   better CK configs for shapes not in tuned CSV (E=257, bs=16)
3. Adaptive KSPLIT: dense->CSV-tuned, sparse->KSPLIT=4, moderate->KSPLIT=2

For dense shapes: use CSV-tuned configs (already near-optimal)
For sparse shapes: online tune + KSPLIT to explore better tile configs
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

    if estimated_m >= 50:
        # Dense: use CSV-tuned CK configs, no online tune overhead
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
        os.environ.pop("AITER_ONLINE_TUNE", None)
    elif num_experts >= 200 and estimated_m < 10:
        # Very sparse (E=257, bs=16): online tune + KSPLIT=4
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
        os.environ["AITER_ONLINE_TUNE"] = "1"
    else:
        # Moderate sparse: KSPLIT=2, no online tune
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
        os.environ.pop("AITER_ONLINE_TUNE", None)

    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids, expert_mask=None,
        activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
        doweight_stage1=True,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
    )
