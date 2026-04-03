"""MXFP4 MoE submission — env-var tuned for MI355X (gfx950).

Optimizations over current submission:
1. AITER_USE_NT=1: Non-transposed weight access (proven 10% improvement)
2. AITER_BYPASS_TUNE_CONFIG=1: Skip CSV config lookup overhead
3. AITER_GFX950_EXPL_SCHED=1: Explicit XCD scheduling for CDNA4
4. sys.path fix for JIT build dirs
5. AITER_JIT_DIR for cache persistence

Key rules (from 18+ phases):
- NEVER use doweight_stage1=True (GPU fault)
- NEVER use expert_mask (CK crash)
- AITER_KSPLIT env var is NOT honored by aiter (computes internally)
"""

import os
import sys

# ── Environment tuning (must be set BEFORE importing aiter) ──
os.environ["AITER_JIT_DIR"] = "/tmp/aiter_jit_cache"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["AITER_GFX950_EXPL_SCHED"] = "1"

# Fix sys.path for JIT .so files
_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in sys.path:
    sys.path.insert(0, _AITER_JIT_DIR)
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
