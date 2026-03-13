"""
MXFP4 MoE — Phase 8: BYPASS_TUNE + Adaptive KSPLIT.

Key discovery: The 257-expert TP=8 benchmark shapes (dhidden=7168, dexpert=256)
ARE in dsv3_fp4_tuned_fmoe.csv with ksplit=0 (CK path). AITER_KSPLIT is ignored
for CSV-tuned shapes. AITER_BYPASS_TUNE_CONFIG=1 forces the heuristic path for
ALL shapes, including CSV-matched ones.

For sparse shapes (estimated_m < 50), cktile (KSPLIT=2) is dramatically faster:
  257E, bs=16:  CK 152.7 µs → cktile 91.6 µs  (-40%)
  257E, bs=128: CK 239   µs → cktile 176  µs  (-26%)
  257E, bs=512: CK 336.5 µs → cktile 284  µs  (-16%)
  33E,  bs=16:  CK 106.2 µs → cktile 60.5 µs  (-43%)
  33E,  bs=128: CK 141.1 µs → cktile 108  µs  (-24%)

For dense shapes (estimated_m >= 50), CK path stays faster:
  33E,  bs=512, dexp=512:  215 µs  (vs ref 225 µs)
  33E,  bs=512, dexp=2048: 353 µs  (vs ref 380 µs)

Expected geomean: ~156 µs (vs 166 µs Phase 6, vs 184 µs baseline).
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
        # Sparse: bypass CSV-tuned configs, force cktile path with split_k=2.
        # CSV configs were tuned at hot-cache; cold-cache benchmarks favor cktile.
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
    else:
        # Dense: use CK MXFP4-optimized path (best for high token density).
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
