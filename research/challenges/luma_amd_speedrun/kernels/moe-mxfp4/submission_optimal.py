"""
MXFP4 MoE — Phase 10: Expert-count-aware KSPLIT selection.

Key discovery: Optimal KSPLIT depends on BOTH estimated_m AND num_experts.
For large expert counts (257E, dexp=256), KSPLIT=4 is better at estimated_m≈4
because smaller expert weight matrices benefit more from K-dimension splitting.
For small expert counts (33E, dexp=512+), KSPLIT=2 remains optimal for sparse.

Phase 9 benchmark data (vs Phase 8 KSPLIT=2 baseline):
  bs=16,  257E (em=0): KSPLIT=4 → 91.3 vs 95.1 µs  (KSPLIT=4 better, -4%)
  bs=128, 257E (em=4): KSPLIT=4 → 172  vs 186  µs  (KSPLIT=4 better, -7.5%)
  bs=512, 257E (em=17): KSPLIT=4 → 284 vs 275  µs  (KSPLIT=2 better, +3.3%)
  bs=16,  33E  (em=4): KSPLIT=4 → 61.4 vs 59.8 µs  (KSPLIT=2 better, +2.7%)

Strategy:
  - num_experts >= 200 AND estimated_m < 10: KSPLIT=4 (large expert count, sparse)
  - estimated_m < 50 (others): KSPLIT=2 (moderate sparse, or small expert count)
  - estimated_m >= 50: KSPLIT=0 (dense, CK MXFP4 path)
  Always BYPASS_TUNE for sparse shapes to override CSV-locked 257E configs.
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

    if estimated_m >= 50:
        # Dense: CK MXFP4-optimized path (ksplit=0).
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif num_experts >= 200 and estimated_m < 10:
        # Large expert count, very sparse: split_k=4 exploits K-parallelism.
        # Smaller expert weights (dexp≈256) benefit more from higher splits.
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
    else:
        # Sparse (few experts or moderate token density): cktile split_k=2.
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"

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
