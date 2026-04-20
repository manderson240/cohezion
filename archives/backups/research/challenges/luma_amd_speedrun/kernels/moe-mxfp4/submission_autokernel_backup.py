"""
MXFP4 MoE: K-Search V=0.5 Adaptive KSPLIT Routing
Pruned: torch.compile (Dynamo crash)
Pruned: expert_mask (GPU memory fault)
"""

import os

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


os.environ["AITER_USE_NT"] = "1"

_state: dict = {"ksplit": None}


def _set_ks(est_m, num_experts):
    # Safe KSPLIT selection: KSPLIT=4 only for 256E (dexp=256, K/4=64 safe)
    # KSPLIT=4 causes catastrophic overflow for 32E/dexp=512 (K/4=128)
    if est_m >= 50:
        target = "0"  # Dense: CK MXFP4 ASM
    elif num_experts >= 200 and est_m < 10:
        target = "4"  # 256E sparse: K-parallelism
    else:
        target = "2"  # 32E sparse: cktile (safe)

    if _state["ksplit"] != target:
        if target == "0":
            os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
            os.environ.pop("AITER_KSPLIT", None)
        else:
            os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
            os.environ["AITER_KSPLIT"] = target
        _state["ksplit"] = target


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

    hp = config["d_hidden_pad"] - config["d_hidden"]
    ip = config["d_expert_pad"] - config["d_expert"]
    ne = gate_up_weight_shuffled.shape[0]
    est_m = topk_ids.numel() // ne

    _set_ks(est_m, ne)

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
        hidden_pad=hp,
        intermediate_pad=ip,
    )
