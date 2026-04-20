"""MXFP4 MoE submission — FP8 block-scaled variant.

Uses fmoe_fp8_blockscale_g1u1 for 3x performance over non-block-scaled.
Requires (128,128) block shape + FP8 weights.

Target: ~120µs (from ~180µs)
Leader: ~110µs
Gap: 1.09x
"""

import os
import sys


os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")
_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in sys.path:
    sys.path.insert(0, _AITER_JIT_DIR)

from aiter import ActivationType
from aiter.fused_moe import fmoe_fp8_blockscale_g1u1
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """MoE with FP8 block-scale for 3x performance."""
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

    # FP8 block-scale requires specific block shape (128,128)
    return fmoe_fp8_blockscale_g1u1(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        activation=ActivationType.Silu,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        # Block scale parameters
        block_size_m=128,
        block_size_n=128,
    )
