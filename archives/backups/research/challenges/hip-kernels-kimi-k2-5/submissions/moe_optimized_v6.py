"""MoE v6: Research-based optimizations."""

import os

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"


def custom_kernel(data: input_t) -> output_t:
    """Optimized based on AITER MoE research.

    Key findings from /tmp/aiter/csrc/kernels/moe_fused_gate.cu:
    - Uses ck_tile for efficient expert dispatch
    - OPUS sorting improves routing efficiency
    - Block size M = 32 is optimal
    - KSPLIT should be adaptive based on estimated tokens per expert

    From /tmp/aiter/hsa/gfx950/fmoe_2stages/:
    - Stage1 kernels: 112x128, 128x128, 144x128, 160x128
    - PF2 and PF3 variants for different parallelism
    """
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

    # Adaptive KSPLIT based on expert count and estimated M
    # From AITER research: higher KSPLIT for sparse workloads
    if ne >= 200:  # 256E configs
        if est_m < 5:
            ks = "4"  # Very sparse
        elif est_m < 15:
            ks = "2"
        else:
            ks = "1"
    else:  # 32E configs
        if est_m < 10:
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
