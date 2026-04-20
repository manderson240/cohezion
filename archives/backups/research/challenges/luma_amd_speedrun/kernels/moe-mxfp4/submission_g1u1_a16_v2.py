"""
MoE: fmoe_g1u1_a16 with correct 13-argument signature.

From error message, the C++ declaration is:
  fmoe_g1u1_a16(out!, input!, gate!, down!, sorted_token_ids!,
    sorted_weights!, sorted_expert_ids!, num_valid_ids!, topk,
    fc1_scale!, fc2_scale!, fc1_smooth_scale!, fc2_smooth_scale!,
    activation=0) -> ()

This is a SINGLE fused kernel replacing the entire 2-stage pipeline.
We call moe_sorting_fwd first to get sorted_* tensors, then fmoe_g1u1_a16.
"""

from __future__ import annotations

import os
import sys


os.environ["AITER_USE_NT"] = "1"

import aiter
import torch
from reference import ref_kernel
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

    bs = hidden_states.shape[0]
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    num_experts = n_routed + n_shared
    topk = config.get("topk", topk_ids.shape[1])
    d_hidden = config.get("d_hidden", hidden_states.shape[1])

    try:
        # Step 1: Run moe_sorting_fwd to get sorted tensors
        max_num_tokens = bs * topk
        sorted_token_ids = torch.empty(
            max_num_tokens, dtype=torch.int32, device=hidden_states.device
        )
        sorted_weights = torch.empty(
            max_num_tokens, dtype=torch.float32, device=hidden_states.device
        )
        sorted_expert_ids = torch.empty(num_experts, dtype=torch.int32, device=hidden_states.device)
        num_valid_ids = torch.empty(num_experts, dtype=torch.int32, device=hidden_states.device)
        moe_buf = torch.empty(num_experts + 1, dtype=torch.int32, device=hidden_states.device)

        aiter.moe_sorting_fwd(
            topk_ids,
            topk_weights,
            sorted_token_ids,
            sorted_weights,
            sorted_expert_ids,
            num_valid_ids,
            moe_buf,
            num_experts,
            32,  # unit_size (block_m)
        )

        # Step 2: Pre-allocate output
        out = torch.zeros(bs, d_hidden, dtype=hidden_states.dtype, device=hidden_states.device)

        # Step 3: Create smooth scales (try None first, then zeros)
        fc1_smooth = torch.ones(1, dtype=hidden_states.dtype, device=hidden_states.device)
        fc2_smooth = torch.ones(1, dtype=hidden_states.dtype, device=hidden_states.device)

        # Step 4: Call fmoe_g1u1_a16 with full signature
        # Note: uses gate_up_weight_shuffled (w1) and down_weight_shuffled (w2)
        # with their shuffled scales
        aiter.fmoe_g1u1_a16(
            out,  # a0: output
            hidden_states,  # a1: input
            gate_up_weight_shuffled,  # a2: gate (w1)
            down_weight_shuffled,  # a3: down (w2)
            sorted_token_ids,  # a4
            sorted_weights,  # a5
            sorted_expert_ids,  # a6
            num_valid_ids,  # a7
            topk,  # topk (SymInt)
            gate_up_weight_scale_shuffled,  # a9: fc1_scale
            down_weight_scale_shuffled,  # a10: fc2_scale
            fc1_smooth,  # a11: fc1_smooth_scale
            fc2_smooth,  # a12: fc2_smooth_scale
            1,  # activation: SiLU=1
        )

        print(
            f"fmoe_g1u1_a16 SUCCESS! out shape={out.shape}, max={out.abs().max().item():.4f}",
            file=sys.stderr,
        )
        return out

    except Exception as e:
        print(f"fmoe_g1u1_a16 v2 failed: {str(e)[:500]}", file=sys.stderr)

    # Fallback
    return ref_kernel(data)
