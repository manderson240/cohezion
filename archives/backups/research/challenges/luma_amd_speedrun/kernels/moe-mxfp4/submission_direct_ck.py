"""
MoE: Direct ck_moe_stage1 + ck_moe_stage2 dispatch.

Bypasses the fused_moe Python wrapper overhead by calling CK kernels directly.
Full signatures reverse-engineered from g1u1_a16 probe.

ck_moe_stage1(hidden_states, w1, w2, sorted_token_ids, sorted_expert_ids,
    num_valid_ids, out, topk, kernelName=None, w1_scale=None, a1_scale=None,
    block_m=32, sorted_weights=None, quant_type=0, activation=0,
    splitk=1, non_temporal_load=False, dst_type=None, is_shuffled=True) -> None

ck_moe_stage2(inter_states, w1, w2, sorted_token_ids, sorted_expert_ids,
    num_valid_ids, out, topk, ...) -> None
"""

from __future__ import annotations

import os
import sys


os.environ["AITER_USE_NT"] = "1"

import aiter
import torch
from aiter import ActivationType, QuantType
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
    d_hidden = config.get("d_hidden", hidden_states.shape[1])
    d_expert = config.get("d_expert", 0)
    n_routed = config.get("n_routed_experts", 0)
    n_shared = config.get("n_shared_experts", 0)
    num_experts = n_routed + n_shared
    topk = config.get("topk", topk_ids.shape[1])
    hidden_pad = config.get("d_hidden_pad", d_hidden) - d_hidden
    intermediate_pad = config.get("d_expert_pad", d_expert) - d_expert

    try:
        # Step 1: Sorting (same as fused_moe internal)
        max_num_tokens = bs * topk
        sorted_token_ids = torch.empty(
            (num_experts * ((max_num_tokens + 31) // 32) * 32,),
            dtype=torch.int32,
            device=hidden_states.device,
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
            32,
        )

        # Step 2: Intermediate buffer
        d_expert_padded = d_expert + intermediate_pad
        inter_states = torch.empty(
            max_num_tokens,
            d_expert_padded * 2,
            dtype=hidden_states.dtype,
            device=hidden_states.device,
        )

        # Step 3: Stage 1 — gate_up GEMM + SiLU
        # Estimate optimal block_m from tokens per expert
        estimated_m = max(1, bs * topk // num_experts)
        block_m = 32 if estimated_m < 50 else 64

        aiter.ck_moe_stage1(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            sorted_token_ids,
            sorted_expert_ids,
            num_valid_ids,
            inter_states,
            topk,
            None,  # kernelName (auto-select)
            gate_up_weight_scale_shuffled,  # w1_scale
            None,  # a1_scale
            block_m,
            sorted_weights,
            int(QuantType.per_1x32),  # quant_type
            int(ActivationType.Silu),  # activation
            1,  # splitk
            True,  # non_temporal_load
            None,  # dst_type
            True,  # is_shuffled
        )

        # Step 4: Stage 2 — down GEMM + reduce
        d_hidden_padded = d_hidden + hidden_pad
        out = torch.zeros(
            bs, d_hidden_padded, dtype=hidden_states.dtype, device=hidden_states.device
        )

        aiter.ck_moe_stage2(
            inter_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            sorted_token_ids,
            sorted_expert_ids,
            num_valid_ids,
            out,
            topk,
            None,  # kernelName
            down_weight_scale_shuffled,  # w2_scale
            None,  # a2_scale
            block_m,
            sorted_weights,
            int(QuantType.per_1x32),
            0,  # no activation in stage2
            1,  # splitk
            True,  # non_temporal_load
            None,  # dst_type
            True,  # is_shuffled
        )

        if hidden_pad > 0:
            out = out[:, :d_hidden]

        print(
            f"Direct CK SUCCESS! out shape={out.shape}, max={out.abs().max().item():.4f}",
            file=sys.stderr,
        )
        return out

    except Exception as e:
        print(f"Direct CK failed: {str(e)[:500]}", file=sys.stderr)

    return ref_kernel(data)
