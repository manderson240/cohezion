"""Probe: moe_sorting_fwd with local_expert_mask parameter.

Key discovery from Phase 18: moe_sorting_fwd has a native local_expert_mask parameter.
Previous expert masking attempts crashed because they applied masking AFTER sorting.
This probe tests masking INSIDE sorting, which may correctly skip empty experts.

For 257-expert shapes with bs=8/topk=9, only ~55/257 experts are active.
Skipping 200 empty experts could save significant sorting + CK dispatch time.
"""

import os
import sys


os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Fix sys.path for JIT builds
_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Try to get direct access to moe_sorting_fwd
_HAS_SORTING = False
try:
    from aiter.moe_op import moe_sorting_fwd
    _HAS_SORTING = True
except ImportError:
    pass


def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    E = gate_up_weight_shuffled.shape[0]
    M = hidden_states.shape[0]
    topk = topk_ids.shape[1]

    # Build expert mask: which experts have at least 1 token routed to them
    if E > 64 and _HAS_SORTING:
        # Only worthwhile for large expert counts (257E shapes)
        # Count tokens per expert
        expert_counts = torch.bincount(topk_ids.view(-1).to(torch.int64), minlength=E)
        expert_mask = (expert_counts > 0).to(torch.int32)

        # Try passing expert_mask to fused_moe
        try:
            return fused_moe(
                hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
                topk_weights, topk_ids,
                expert_mask=expert_mask,
                activation=ActivationType.Silu,
                quant_type=QuantType.per_1x32,
                doweight_stage1=False,
                w1_scale=gate_up_weight_scale_shuffled,
                w2_scale=down_weight_scale_shuffled,
                a1_scale=None, a2_scale=None,
                hidden_pad=hidden_pad,
                intermediate_pad=intermediate_pad,
            )
        except Exception:
            pass  # Fall through to standard path

    # Standard path
    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
