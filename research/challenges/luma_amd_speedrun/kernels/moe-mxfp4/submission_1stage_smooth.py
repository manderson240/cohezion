"""
MXFP4 MoE — Phase 12k: 1-stage with fc2_smooth_scale fix.

Discovery: fmoe_int8_g1u0 requires fc2_smooth_scale as a Tensor.
For MXFP4 per_1x32 without actual SmoothQuant, torch.ones() is
the identity (no-op scaling).

If 1-stage works: single fused kernel vs 4+ kernel launches in 2-stage.
Falls back to Phase 12j (doweight=False, adaptive KSPLIT) on any error.
"""
import sys
import os
import torch
from task import input_t, output_t
from aiter.fused_moe import fused_moe
from aiter import ActivationType, QuantType

_probed = False
_1stage_fn = None
_sort_fn = None


def _probe():
    global _probed, _1stage_fn, _sort_fn
    if _probed:
        return
    _probed = True
    try:
        from aiter.fused_moe import fused_moe_1stage
        _1stage_fn = fused_moe_1stage
    except ImportError:
        print("fused_moe_1stage not importable", file=sys.stderr)
    try:
        import aiter
        _sort_fn = aiter.moe_sorting_fwd
    except AttributeError:
        print("moe_sorting_fwd not available on aiter", file=sys.stderr)


def _fallback(hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
              gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
              topk_weights, topk_ids, hidden_pad, intermediate_pad,
              num_experts):
    estimated_m = topk_ids.numel() // num_experts
    if estimated_m >= 50:
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    elif num_experts >= 200 and estimated_m < 10:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
    else:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"

    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids, expert_mask=None,
        activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
    )


def custom_kernel(data: input_t) -> output_t:
    _probe()

    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    num_experts = gate_up_weight_shuffled.shape[0]
    M = hidden_states.shape[0]
    topk = topk_ids.shape[1]
    d_expert = config["d_expert"]

    if _1stage_fn is not None and _sort_fn is not None:
        try:
            block_size_M = 64 if M * topk // num_experts >= 10 else 32
            unit_size = block_size_M

            sorted_token_ids = torch.empty(
                (num_experts * (M * topk // num_experts + unit_size)),
                dtype=torch.int32, device=hidden_states.device,
            )
            sorted_weights = torch.empty_like(
                sorted_token_ids, dtype=torch.float32,
            )
            sorted_expert_ids = torch.empty(
                (num_experts * (M * topk // num_experts // unit_size + 1),),
                dtype=torch.int32, device=hidden_states.device,
            )
            num_valid_ids = torch.empty(
                1, dtype=torch.int32, device=hidden_states.device,
            )
            moe_buf = torch.empty(
                (M, config["d_hidden"]),
                dtype=hidden_states.dtype, device=hidden_states.device,
            )

            _sort_fn(
                topk_ids, topk_weights,
                sorted_token_ids, sorted_weights,
                sorted_expert_ids, num_valid_ids,
                moe_buf,
                num_experts, unit_size,
            )

            # Identity smooth scale — no-op for MXFP4 per_1x32
            fc2_smooth = torch.ones(
                d_expert, dtype=hidden_states.dtype,
                device=hidden_states.device,
            )

            _1stage_fn(
                hidden_states,
                gate_up_weight_shuffled,
                down_weight_shuffled,
                topk,
                sorted_token_ids,
                sorted_weights,
                sorted_expert_ids,
                num_valid_ids,
                moe_buf,
                isG1U1=False,
                block_size_M=block_size_M,
                activation=ActivationType.Silu,
                quant_type=QuantType.per_1x32,
                q_dtype_a=torch.float4_e2m1fn_x2,
                q_dtype_w=torch.float4_e2m1fn_x2,
                w1_scale=gate_up_weight_scale_shuffled,
                w2_scale=down_weight_scale_shuffled,
                a1_scale=None,
                a2_scale=None,
                fc2_smooth_scale=fc2_smooth,
                M=M,
                device=hidden_states.device,
                doweight_stage1=False,
            )
            return moe_buf

        except Exception as e:
            print(f"1STAGE_SMOOTH_ERR: {e}", file=sys.stderr)

    return _fallback(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, hidden_pad, intermediate_pad,
        num_experts,
    )
