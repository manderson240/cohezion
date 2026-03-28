"""
MXFP4 MoE: doweight_stage1 + OPUS sorting + optimal hybrid KSPLIT + NT.

Combines three optimizations:
1. doweight_stage1=True: fuses topk weight application into stage1 kernel
2. OPUS MOE sorting: alternative token sorting (env var)
3. Shape-aware KSPLIT routing based on benchmark data:
   - est_m >= 100: default tuned config
   - est_m >= 16 AND E > 100: default (fragmented + medium density)
   - else: ksplit=4 (sparse, split-K helps)
"""
import os
from task import input_t, output_t
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe

os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"

_state: dict = {"ksplit": None}


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

    if estimated_m >= 100:
        ks = "default"
    elif estimated_m >= 16 and num_experts > 100:
        ks = "default"
    else:
        ks = "4"

    if _state["ksplit"] != ks:
        if ks == "default":
            os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
            os.environ.pop("AITER_KSPLIT", None)
        else:
            os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
            os.environ["AITER_KSPLIT"] = ks
        _state["ksplit"] = ks

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
