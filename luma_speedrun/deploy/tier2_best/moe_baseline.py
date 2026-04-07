#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M2: Shape-aware KSPLIT for ranked shapes.

Ranked shapes:
  d_expert=256, n_routed=256, bs=16/128/512  (3 shapes — tiny GEMMs!)
  d_expert=512, n_routed=32, bs=16/128/512   (3 shapes)
  d_expert=2048, n_routed=32, bs=512         (1 shape)

For d_expert=256: K=256 is very small. KSPLIT should be 0 (no split)
because splitting tiny K adds overhead.
For d_expert=2048: K=2048 is medium. KSPLIT=1 might help.

Also: for 256 experts with bs=16 and topk=8, only 128 tokens total
routed to 256 experts → ~0.5 tokens/expert. Very sparse!
"""

from __future__ import annotations
import os

os.environ["AITER_USE_NT"] = "1"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


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
    d_expert = config.get("d_expert", 0)

    # Shape-aware KSPLIT
    if d_expert <= 512:
        os.environ["AITER_KSPLIT"] = "0"  # No split for tiny K
    else:
        os.environ.pop("AITER_KSPLIT", None)  # Default for large K

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
