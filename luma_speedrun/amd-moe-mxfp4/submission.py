"""MXFP4 MoE submission — optimized for MI355X (gfx950).

Optimizations over reference:
1. sys.path fix for JIT build dirs (prevents JIT lookup failures)
2. AITER_JIT_DIR set for cache persistence (mitigates 720s timeout)
3. Direct fused_moe call with optimal parameters (Phase 18 exhaustion confirmed)
4. No warmup — prevents CK autotuning cache poisoning from 8-expert dummy shapes

Current: ~180µs | Leader: ~110µs | Gap: 1.6x
Warmup removal expected to recover ~25µs (8-expert cache poisoning eliminated).

Key rules (from 18 phases of experimentation):
- NEVER use doweight_stage1=True (GPU fault or 82% mismatch)
- NEVER use KSPLIT=4 for 32-expert shapes (catastrophic overflow)
- fmoe_g1u1 is dead (NaN for 32-expert, no gain for 256-expert)
- expert_mask crashes CK stage1 kernel
"""

import os
import sys


# JIT cache — may help with 720s timeout on repeated submissions
os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")

# Fix sys.path: JIT .so files live at /home/runner/aiter/aiter/jit/
# NOT in the build/ subdirectories (those are compilation intermediates)
_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in sys.path:
    sys.path.insert(0, _AITER_JIT_DIR)
# Also add build subdirs as fallback
_AITER_JIT_BUILD = os.path.join(_AITER_JIT_DIR, "build")
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

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
