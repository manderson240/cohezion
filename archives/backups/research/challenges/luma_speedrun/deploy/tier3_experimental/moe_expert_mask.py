"""MXFP4 MoE submission — expert_mask variant for sparse expert dispatch.

For 256-expert shapes with bs=8-32, most experts (~200) receive zero tokens.
The moe_sorting_fwd kernel has native local_expert_mask support that can skip
empty experts in sorting+dispatch, reducing CK kernel work.

Previous expert_mask attempts crashed CK stage1 — but those used a different
mask format. The local_expert_mask parameter in moe_sorting_fwd expects int32.

Risk: MEDIUM — may crash or produce incorrect results.
Expected gain: ~10-15µs if it works (skip 200+ empty expert dispatches).
"""

import os
import sys


os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")

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

    # Get num_experts from weight shape (first dim = num_experts)
    num_experts = gate_up_weight_shuffled.shape[0]

    # Compute which experts actually have tokens assigned
    expert_counts = torch.bincount(
        topk_ids.flatten().to(torch.int64),
        minlength=num_experts,
    )
    expert_mask = (expert_counts > 0).to(torch.int32)

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=expert_mask,
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
