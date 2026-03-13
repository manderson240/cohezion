"""
MXFP4 MoE — Phase 9: BYPASS_TUNE + Tiered KSPLIT (4 for very sparse, 2 for sparse).

cktile split_k is a runtime parameter (same JIT module), so KSPLIT=4 has no
additional JIT cost. Test if higher split_k helps very sparse cases (estimated_m < 10):
  - bs=16,  257E: estimated_m=0  → KSPLIT=4 (vs 2 in Phase 8)
  - bs=128, 257E: estimated_m=4  → KSPLIT=4 (vs 2 in Phase 8)
  - bs=16,   33E: estimated_m=4  → KSPLIT=4 (vs 2 in Phase 8)
  - bs=512, 257E: estimated_m=17 → KSPLIT=2 (same as Phase 8)
  - bs=128,  33E: estimated_m=34 → KSPLIT=2 (same as Phase 8)

Phase 8 reference (156 µs geomean):
  bs=16,  257E: 90.5 µs | bs=128, 257E: 177 µs | bs=512, 257E: 274 µs
  bs=16,   33E: 61.1 µs | bs=128,  33E: 114 µs | bs=512, 33E(512): 214 µs
  bs=512, 33E(2048): 344 µs
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

    os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

    if estimated_m < 10:
        # Very sparse: higher split_k = more K-parallelism, better GPU utilization
        os.environ["AITER_KSPLIT"] = "4"
    elif estimated_m < 50:
        # Moderately sparse: split_k=2 is optimal
        os.environ["AITER_KSPLIT"] = "2"
    else:
        # Dense: CK MXFP4-optimized path (split_k=0)
        os.environ.pop("AITER_KSPLIT", None)

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
