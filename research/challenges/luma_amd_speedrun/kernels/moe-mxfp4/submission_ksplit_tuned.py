"""
MXFP4 MoE — Phase 12l: Fine-grained KSPLIT routing.

Hypothesis: KSPLIT=1 (no split-K) may be better for moderate shapes
where the GEMM is large enough but split-K reduction adds overhead.

Routing:
- estimated_m < 5:   cktile KSPLIT=4 (very sparse, maximize CU utilization)
- 5 ≤ m < 20:        cktile KSPLIT=2 (moderate-sparse)
- 20 ≤ m < 80:       cktile KSPLIT=1 (moderate — avoid split-K reduction)
- m ≥ 80:            CK CSV-tuned (dense — use CSV's optimized configs)

All shapes: doweight_stage1=False (BROKEN on both paths).
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

    if estimated_m >= 80:
        # Dense: CK CSV-tuned path
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif estimated_m >= 20:
        # Moderate: cktile without split-K (avoid reduction overhead)
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "1"
    elif estimated_m >= 5:
        # Moderate-sparse: split-K=2
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
    else:
        # Very sparse: split-K=4
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"

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
