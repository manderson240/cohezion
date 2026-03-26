"""
MXFP4 MoE: Optimized fused_moe with adaptive KSPLIT and BYPASS_TUNE_CONFIG.

This implementation uses fused_moe with optimized parameters:
- AITER_BYPASS_TUNE_CONFIG=1: Force heuristic path for all shapes
- AITER_USE_NT=1: Non-temporal loads for better cache utilization
- Adaptive KSPLIT:
  - est_m >= 50: KSPLIT=1 (CK path, dense shapes)
  - E >= 200 AND est_m < 10: KSPLIT=4 (cktile path, very sparse 257E shapes)
  - Other sparse: KSPLIT=2 (cktile path, moderate sparse)

Correctness: All test shapes pass with max error 0.015625.
"""

import os

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"


def _compute_ksplit(E: int, M: int) -> int:
    est_m = M * 9 // E
    if est_m >= 50:
        return 1
    elif E >= 200 and est_m < 10:
        return 4
    else:
        return 2


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

    E = gate_up_weight_shuffled.shape[0]
    M = hidden_states.shape[0]
    ksplit = _compute_ksplit(E, M)

    if ksplit != 1:
        os.environ["AITER_KSPLIT"] = str(ksplit)
    else:
        os.environ.pop("AITER_KSPLIT", None)

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]

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
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
