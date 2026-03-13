"""
MXFP4 MoE — Phase 8: AITER_BYPASS_TUNE_CONFIG + Adaptive KSPLIT.

Key insight: The 257-expert TP=8 shapes (dexpert=256, dhidden=7168) ARE in
dsv3_fp4_tuned_fmoe.csv with ksplit=0 (CK path). AITER_KSPLIT is ignored for
CSV-tuned shapes. AITER_BYPASS_TUNE_CONFIG=1 forces the heuristic path for ALL
shapes including CSV-matched ones.

For benchmark shapes with estimated_m < 50 (all TP=8 shapes + TP=4 bs=16/128):
  - Without bypass: CSV overrides → ksplit=0 → CK kernel
  - With bypass: heuristic → AITER_KSPLIT=2 → cktile path (split_k=2)

Hypothesis: CSV tuning was done at hot-cache. Cold-cache benchmarks (actual
competition) may favor cktile due to better K-parallelism on sparse token distributions.
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

    if estimated_m < 50:
        # Force off CSV-tuned path + use cktile with split_k=2
        # (Affects TP=8 shapes that are normally CSV-locked to ksplit=0)
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
    else:
        # Dense: let CSV/heuristic pick ksplit=0 → CK path
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
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
