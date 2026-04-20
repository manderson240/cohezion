"""MoE Breakthrough: Adaptive KSPLIT for Top 10.

Target: 145µs (leader) vs current ~155µs
Strategy: Aggressive KSPLIT for sparse, conservative for dense
"""

import os

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"


def custom_kernel(data: input_t) -> output_t:
    """Optimized MoE with adaptive KSPLIT for MI355X."""
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

    hp = config["d_hidden_pad"] - config["d_hidden"]
    ip = config["d_expert_pad"] - config["d_expert"]
    ne = gate_up_weight_shuffled.shape[0]
    M = hidden_states.shape[0]
    topk = topk_ids.shape[1]

    # Calculate estimated tokens per expert
    est_m = (M * topk) / ne

    # Ultra-aggressive KSPLIT based on sparsity
    if ne >= 200:  # 256E configs - very sparse
        if est_m < 3:
            ks = "8"  # Maximum parallelism
        elif est_m < 8:
            ks = "6"
        elif est_m < 15:
            ks = "4"
        elif est_m < 30:
            ks = "2"
        else:
            ks = "1"
    else:  # 32E configs - less sparse
        if est_m < 5:
            ks = "4"
        elif est_m < 15:
            ks = "2"
        else:
            ks = "1"

    os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
    os.environ["AITER_KSPLIT"] = ks

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,  # CRITICAL: Never use True
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hp,
        intermediate_pad=ip,
    )
