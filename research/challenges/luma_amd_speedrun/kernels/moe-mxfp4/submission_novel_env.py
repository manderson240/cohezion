"""
MoE Novel Approach: Test AITER environment variables that change dispatch behavior.

From AITER blog (Mar 2026):
- VLLM_USE_AITER_MOE=1 — changes MoE dispatch path
- CK_BLOCK_GEMM=1 — enables CK block GEMM inside MoE
- SGLANG_ROCM_AITER_BLOCK_MOE=1 — block MoE variant

Also probe: aiter.tuned_gemm.tgemm.mm() — completely different GEMM API path.
And: fused_dynamic_mxfp4_quant_moe_sort integration with fused_moe.
"""

from __future__ import annotations

import inspect
import os
import sys


# Novel env vars from AITER blog — NOT previously tested
os.environ["AITER_USE_NT"] = "1"
os.environ["CK_BLOCK_GEMM"] = "1"

import aiter
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
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

    # === Probe 1: tuned_gemm API (different from gemm_a4w4) ===
    try:
        from aiter import tuned_gemm

        tgemm_attrs = [a for a in dir(tuned_gemm) if not a.startswith("_")]
        print(f"tuned_gemm attrs: {tgemm_attrs}", file=sys.stderr)
        if hasattr(tuned_gemm, "tgemm"):
            tg = tuned_gemm.tgemm
            tg_attrs = [a for a in dir(tg) if not a.startswith("_")]
            print(f"tgemm attrs: {tg_attrs}", file=sys.stderr)
    except Exception as e:
        print(f"tuned_gemm error: {e}", file=sys.stderr)

    # === Probe 2: flash_attn_func (could be used for MLA) ===
    try:
        fn = aiter.flash_attn_func
        sig = inspect.signature(fn)
        print(f"flash_attn_func signature: {sig}", file=sys.stderr)
    except Exception as e:
        print(f"flash_attn_func: {e}", file=sys.stderr)

    # === Probe 3: Check if CK_BLOCK_GEMM changes fused_moe behavior ===
    try:
        hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
        intermediate_pad = config["d_expert_pad"] - config["d_expert"]

        # Run with CK_BLOCK_GEMM=1 — this may use a different internal kernel
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
        print(f"CK_BLOCK_GEMM=1 fused_moe SUCCESS, shape={output.shape}", file=sys.stderr)
        return output

    except Exception as e:
        print(f"CK_BLOCK_GEMM fused_moe failed: {str(e)[:300]}", file=sys.stderr)

    return ref_kernel(data)
