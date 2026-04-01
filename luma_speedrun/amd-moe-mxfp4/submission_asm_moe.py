"""MXFP4 MoE submission — asm_moe path for maximum performance.

Uses aiter's asm_moe() which is hand-tuned ASM with auto-dispatch.
Claims "best performance on AMD platform".
Supports BF16/A16W8/A8W8/INT8/FP8.

Target: ~140µs (from ~180µs)
Leader: ~110µs
Gap: 1.27x
"""

import os
import sys


os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")
_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in sys.path:
    sys.path.insert(0, _AITER_JIT_DIR)

from aiter import ActivationType, QuantType
from aiter.fused_moe import asm_moe
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """MoE with asm_moe ASM path."""
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

    # asm_moe - hand-tuned ASM kernel
    return asm_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
