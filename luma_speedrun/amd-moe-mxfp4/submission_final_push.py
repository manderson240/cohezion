"""
MoE Ultimate 4-Tier v2: Expert-count-aware KSPLIT strategy.

Data-driven from benchmark results:
- Universal KSPLIT=2: 30% better on E=256 sparse, 2x WORSE on dense d=2048
- KSPLIT=6: correct for ultra-sparse, untested benchmark
- CSV defaults: optimal for dense shapes (est_m >= 50)

Strategy:
  est_m >= 50: Default CSV (don't bypass — CSV is tuned for these)
  ne >= 200 AND est_m < 5: KSPLIT=6 (ultra-sparse many-expert, CK-Tile)
  est_m >= 10: KSPLIT=2 (moderate, triggers CK-Tile path)
  est_m >= 5:  KSPLIT=4 (sparse, triggers CK-Tile path)
  est_m < 5:   KSPLIT=4 (sparse few-expert, conservative)
"""

import os

os.environ["CK_BLOCK_GEMM"] = "1"
os.environ["AITER_USE_NT"] = "1"

from task import input_t, output_t
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe


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
    ne = config.get("n_routed_experts", gate_up_weight_shuffled.shape[0])
    est_m = topk_ids.numel() // ne

    # Expert-count-aware adaptive KSPLIT
    if est_m >= 50:
        # Dense: CSV-tuned configs are optimal
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif ne >= 200 and est_m < 5:
        # Ultra-sparse many-expert (E=256): max KSPLIT
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "6"
    elif est_m >= 10:
        # Medium: moderate KSPLIT, triggers CK-Tile
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
    else:
        # Sparse: higher KSPLIT
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"

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
