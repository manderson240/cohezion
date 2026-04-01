import os


os.environ["CK_BLOCK_GEMM"] = "1"
os.environ["AITER_USE_NT"] = "1"

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    (hidden_states, gate_up_weight, down_weight, gate_up_weight_scale,
     down_weight_scale, gate_up_weight_shuffled, down_weight_shuffled,
     gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
     topk_weights, topk_ids, config) = data

    hp = config["d_hidden_pad"] - config["d_hidden"]
    ip = config["d_expert_pad"] - config["d_expert"]
    ne = gate_up_weight_shuffled.shape[0]
    est_m = topk_ids.numel() // ne

    # Adaptive KSPLIT with CK_BLOCK_GEMM dispatch
    if est_m >= 50:
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif ne >= 200 and est_m < 10:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
    else:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"

    return fused_moe(hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
                     topk_weights, topk_ids, expert_mask=None,
                     activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
                     doweight_stage1=False, w1_scale=gate_up_weight_scale_shuffled,
                     w2_scale=down_weight_scale_shuffled, a1_scale=None, a2_scale=None,
                     hidden_pad=hp, intermediate_pad=ip)
