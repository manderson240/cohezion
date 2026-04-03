"""MXFP4 MoE submission — splitk + block_size_M tuned for MI355X.

Key optimizations from aiter source analysis:
1. Pass `splitk` directly to fused_moe (avoids env var indirection)
2. Pass `block_size_M` explicitly for shape-dependent tiling
3. All env var tuning (USE_NT, BYPASS, EXPL_SCHED)
4. Shape-dependent parameter selection based on expert count and batch size

From aiter/fused_moe.py source:
- get_ksplit: only activates when token * topk <= expert (decode scenario)
- use_nt: True when (token * topk // e) < 64
- block_size_M: selected from [32, 64, 128] based on CU utilization

MoE tolerance: rtol=5e-2, atol=5e-2 (5% — quite loose)
"""

import os
import sys

# Environment tuning (before imports)
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


def _select_params(num_experts: int, bs: int, d_expert: int) -> tuple[int, int]:
    """Select optimal splitk and block_size_M based on shape.

    Based on aiter's get_ksplit() and get_block_size_M() heuristics:
    - splitk: 0 (auto), 1, 2, or 3 (max for precision)
    - block_size_M: 32, 64, or 128

    Key insight: splitk only helps in decode scenarios where
    token_count * topk <= num_experts (few tokens per expert).
    """
    # Estimate tokens per expert
    topk = 8  # DeepSeek R1 uses top-8
    est_m = max(1, (bs * topk) // num_experts)

    # splitk: helps when est_m is small (decode-like)
    if est_m <= 2:
        splitk = 3  # max split for very sparse
    elif est_m <= 8:
        splitk = 2
    elif est_m <= 16:
        splitk = 1
    else:
        splitk = 0  # no split needed, enough work per expert

    # block_size_M: smaller blocks for sparse, larger for dense
    if est_m <= 4:
        block_m = 32
    elif est_m <= 32:
        block_m = 64
    else:
        block_m = 128

    return splitk, block_m


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
    num_experts = gate_up_weight_shuffled.shape[0]
    bs = hidden_states.shape[0]

    splitk, block_m = _select_params(num_experts, bs, config["d_expert"])

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
        block_size_M=block_m,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
        splitk=splitk,
    )
