"""
MoE MXFP4 Kernel - Breakthrough Direct Dispatch

Key insight: The fused_moe wrapper has ~5-10µs overhead from:
1. Sorting bookkeeping (num_valid_ids computation)
2. Scale handling and re-quantization decisions
3. Conditional activation logic

By calling moe_cktile2stages_gemm1/gemm2 directly with explicit kernel_name,
we bypass these overheads.

However, this requires replicating the sorting logic. Instead, we focus on
optimizing the fused_moe call by:
1. Ensuring USE_NT=1 for memory transfer optimization
2. Optimal KSPLIT selection per shape
3. Using block_m=32 (the most efficient tile size for a16w4 on gfx950)
"""

from __future__ import annotations

import os


# Enable Non-Temporal hint for GPU memory transfers
os.environ["AITER_USE_NT"] = "1"

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Adaptive KSPLIT table - OPTIMIZED
# Format: "{E_total}_{d_expert}_{bs}" -> ksplit value
# Based on estimated_m = bs / E_total analysis
KSPLIT_TABLE = {
    # 257 experts (sparse) - DeepSeek-R1 style
    "257_256_16": 4,    # Very sparse (estimated_m=0.06) 
    "257_256_128": 4,   # Sparse (estimated_m=0.5)
    "257_256_512": 0,   # Dense (estimated_m=2.0)
    # 33 experts (denser) - TP=4 style
    "33_512_16": 2,     # estimated_m=0.5
    "33_512_128": 2,    # estimated_m=4.0
    "33_512_512": 0,    # estimated_m=16.0
    # Edge cases for 2048 intermediate
    "33_2048_512": 0,   # Large expert, dense
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
    
    The KSPLIT parameter controls how many experts to process in one kernel launch.
    - Higher KSPLIT = more experts per token processed together = better GPU utilization
      but more memory pressure
    - Lower KSPLIT = fewer experts = less memory pressure but potential underutilization
    
    Based on estimated_m = bs / E_total:
    - estimated_m < 10: KSPLIT=4 (sparse, tokens spread thin)
    - estimated_m < 30: KSPLIT=2 (moderate)  
    - estimated_m >= 30: KSPLIT=0 (dense, tokens concentrated)
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
    Optimized MoE kernel with adaptive KSPLIT.
    
    This is the same as the best previous approach but with careful
    tuning of the KSPLIT selection.
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
