"""
MoE Submission: Optimized MoE using aiter fused_moe.

This uses the official reference implementation as baseline.
"""

#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t


MXFP4_BLOCK_SIZE = 32
PAD_ALIGN = 256


def _pad_to(x: int, align: int) -> int:
    return (x + align - 1) // align * align


def custom_kernel(data: input_t) -> output_t:
    """
    MoE layer using aiter fused_moe.
    """
    (
        hidden_states,
        topk_weights,
        topk_indices,
        w1_list,
        w1_scale_list,
        w2_list,
        w2_scale_list,
        config,
    ) = data

    d_hidden = config["d_hidden"]
    d_expert = config["d_expert"]
    n_routed_experts = config["n_routed_experts"]
    n_shared_experts = config["n_shared_experts"]
    routed_top_k = config["routed_top_k"]
    total_top_k = config["total_top_k"]

    # Convert lists to concatenated tensors
    w1 = torch.cat([w.view(w.shape[0], -1) for w in w1_list], dim=0)
    w2 = torch.cat([w.view(w.shape[0], -1) for w in w2_list], dim=0)

    # Scales
    w1_scale = torch.cat([s.view(s.shape[0], -1) for s in w1_scale_list], dim=0)
    w2_scale = torch.cat([s.view(s.shape[0], -1) for s in w2_scale_list], dim=0)

    # Shuffle weights for better memory access
    w1_shuffled = shuffle_weight(w1.view(-1, d_expert // 2, 2), layout=(16, 16))
    w2_shuffled = shuffle_weight(w2.view(-1, d_hidden // 2, 2), layout=(16, 16))

    # Call fused_moe
    output = fused_moe(
        hidden_states,
        w1_shuffled,
        w2_shuffled,
        topk_weights,
        topk_indices,
        w1_scale=w1_scale,
        w2_scale=w2_scale,
        activation=ActivationType.SiLU,
        quant=QuantType.per_1x32,
    )

    return output
