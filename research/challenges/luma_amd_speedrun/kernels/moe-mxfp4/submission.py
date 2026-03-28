"""
MXFP4 MoE — Phase 12j: Adaptive KSPLIT, doweight DISABLED.

CRITICAL: doweight_stage1=True is BROKEN on BOTH paths:
- cktile (KSPLIT>0): GPU memory fault (nil pointer deref)
- CK (KSPLIT=0): Wrong results (82% element mismatch, mulWeightStage1 bug)
doweight_stage1 must be False for ALL shapes.

Strategy (KSPLIT routing only):
- Dense (estimated_m >= 50): CK path (CSV-tuned, KSPLIT=0)
- Very sparse (E >= 200, m < 10): cktile KSPLIT=4
- Moderate: cktile KSPLIT=2

Benchmark (5/7 shapes from Phase 12e, before doweight failure):
  E=257 bs=16: 90.9µs | E=257 bs=128: 172µs | E=257 bs=512: 282µs
  E=33 bs=16: 59.9µs  | E=33 bs=128: 108µs
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
        # Dense: CK path (CSV-tuned, KSPLIT=0)
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif num_experts >= 200 and estimated_m < 10:
        # Very sparse (E=257, small bs): cktile KSPLIT=4
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
    else:
        # Moderate: cktile KSPLIT=2
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
