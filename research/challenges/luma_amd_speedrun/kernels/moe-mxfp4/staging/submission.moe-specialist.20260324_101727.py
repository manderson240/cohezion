"""
MoE MXFP4 Kernel - Combined USE_NT=1 + Adaptive KSPLIT

Combining two previously-tested improvements:
1. USE_NT=1: 178µs ranked (improvement from baseline ~186µs)
2. Adaptive KSPLIT table: Best found per tree search

Key insight: estimated_m = total_tokens / num_experts determines optimal KSPLIT:
- estimated_m < 10: KSPLIT=4 (sparse experts, low token-per-expert ratio)
- estimated_m < 30: KSPLIT=2 (medium sparsity)
- estimated_m >= 30: KSPLIT=0 (dense, tokens spread across experts)

Target: < 165µs ranked (from current ~186µs)
"""

from __future__ import annotations

import os


# Enable Non-Temporal hint for GPU memory transfers (178µs improvement)
os.environ["AITER_USE_NT"] = "1"

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Adaptive KSPLIT table from tree search
# Format: "{E_total}_{d_expert}_{bs}" -> ksplit value
# E_total = n_routed_experts + n_shared_experts
# d_expert = intermediate dimension per expert
# bs = batch size (number of tokens)
KSPLIT_TABLE = {
    "257_256_16": 4,
    "257_256_128": 4,
    "257_256_512": 0,
    "33_512_16": 2,
    "33_512_128": 2,
    "33_512_512": 0,
    "33_2048_512": 0,
}


def _get_ksplit_key(config: dict) -> str:
    """Build the shape key from config."""
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    d_expert = config.get("d_expert", 0)
    bs = config.get("bs", 0)
    return f"{n_routed + n_shared}_{d_expert}_{bs}"


def _choose_ksplit(config: dict) -> int:
    """
    Adaptive KSPLIT selection based on shape characteristics.
    
    Uses estimated_m = total_tokens / num_experts to determine:
    - KSPLIT=4: Very sparse (estimated_m < 10)
    - KSPLIT=2: Moderately sparse (estimated_m < 30)  
    - KSPLIT=0: Dense (estimated_m >= 30)
    """
    # First try exact match in table
    key = _get_ksplit_key(config)
    if key in KSPLIT_TABLE:
        return KSPLIT_TABLE[key]
    
    # Fallback: compute estimated_m
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    bs = config.get("bs", 0)
    E_total = n_routed + n_shared
    
    if E_total == 0 or bs == 0:
        return 0
    
    estimated_m = bs / E_total
    
    if estimated_m < 10:
        return 4
    elif estimated_m < 30:
        return 2
    else:
        return 0


def custom_kernel(data: input_t) -> output_t:
    """
    Combined MoE kernel with USE_NT=1 and adaptive KSPLIT.
    
    Input data tuple:
        hidden_states:                [M, d_hidden]                           bf16
        gate_up_weight:               [E, 2*d_expert_pad, d_hidden_pad//2]    fp4x2  (raw)
        down_weight:                  [E, d_hidden_pad, d_expert_pad//2]      fp4x2  (raw)
        gate_up_weight_scale:         [E, 2*d_expert_pad, scale_K]            e8m0   (raw)
        down_weight_scale:            [E, d_hidden_pad, scale_K]              e8m0   (raw)
        gate_up_weight_shuffled:      [E, 2*d_expert_pad, d_hidden_pad//2]    fp4x2  (shuffled)
        down_weight_shuffled:         [E, d_hidden_pad, d_expert_pad//2]      fp4x2  (shuffled)
        gate_up_weight_scale_shuffled:[padded, flat]                          e8m0   (shuffled)
        down_weight_scale_shuffled:   [padded, flat]                          e8m0   (shuffled)
        topk_weights:                 [M, total_top_k]                        float32
        topk_ids:                     [M, total_top_k]                        int32
        config:                       dict

    Returns:
        output: [M, d_hidden] bf16
    """
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

    # Adaptive KSPLIT selection
    ksplit = _choose_ksplit(config)
    if ksplit > 0:
        os.environ["AITER_KSPLIT"] = str(ksplit)
    else:
        os.environ.pop("AITER_KSPLIT", None)

    output = fused_moe(
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

    return output
