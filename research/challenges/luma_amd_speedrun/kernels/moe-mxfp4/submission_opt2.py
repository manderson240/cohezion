"""
MoE MXFP4 Kernel - Optimization with explicit block_m forcing

Based on kernel selection logs, try forcing block_m=16 for small batches
and block_m=32 for larger batches via AITER_BLOCK_M env var.
"""

from __future__ import annotations

import os


# Enable Non-Temporal hint for GPU memory transfers
os.environ["AITER_USE_NT"] = "1"

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Adaptive KSPLIT table from tree search
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
    """Adaptive KSPLIT selection based on shape characteristics."""
    key = _get_ksplit_key(config)
    if key in KSPLIT_TABLE:
        return KSPLIT_TABLE[key]
    
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
    """MoE kernel with explicit block_m hints."""
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

    # Force block_m based on batch size for better tile efficiency
    bs = config.get("bs", 0)
    if bs <= 64:
        os.environ["AITER_BLOCK_M"] = "16"
    elif bs <= 256:
        os.environ["AITER_BLOCK_M"] = "32"
    else:
        os.environ["AITER_BLOCK_M"] = "64"

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
