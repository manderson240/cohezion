"""
MXFP4 MoE — Phase 13a: Direct cktile with custom block_m tuning.

Bypasses fused_moe() entirely to call cktile_moe_gemm1/gemm2 directly.
This gives us explicit control over block_m and split_k per shape.

Key insight: fused_moe auto-selects block_m={32,64} based on estimated_m,
but these may not be optimal. Direct calls let us test block_m={16,32,64,128}.

Architecture:
  1. moe_sorting_fwd -> sorted tokens/experts/weights
  2. cktile_moe_gemm1 -> gate+up GEMM with SiLU activation
  3. cktile_moe_gemm2 -> down GEMM with topk weight application

Falls back to fused_moe if any import or runtime error occurs.
"""
import sys
import os
import torch
from task import input_t, output_t
from aiter import ActivationType, QuantType

_initialized = False
_sorting_fn = None
_gemm1_fn = None
_gemm2_fn = None


def _init():
    global _initialized, _sorting_fn, _gemm1_fn, _gemm2_fn
    if _initialized:
        return
    _initialized = True

    # Import sorting
    try:
        import aiter as _aiter
        _sorting_fn = _aiter.moe_sorting_fwd
        print("SORT: imported from aiter.moe_sorting_fwd", file=sys.stderr)
    except AttributeError:
        try:
            from aiter.ops.shuffle import moe_sorting_fwd
            _sorting_fn = moe_sorting_fwd
            print("SORT: imported from aiter.ops.shuffle", file=sys.stderr)
        except ImportError:
            print("SORT_IMPORT_FAIL", file=sys.stderr)

    # Import cktile kernels — correct names: moe_cktile2stages_gemm1/gemm2
    try:
        import aiter as _aiter
        _gemm1_fn = _aiter.moe_cktile2stages_gemm1
        _gemm2_fn = _aiter.moe_cktile2stages_gemm2
        print("CKTILE: imported moe_cktile2stages_gemm1/2", file=sys.stderr)
    except AttributeError:
        print("CKTILE_IMPORT_FAIL", file=sys.stderr)


def _select_params(num_experts, estimated_m):
    """Select block_m and split_k based on shape characteristics."""
    if estimated_m < 5:
        return 32, 4
    elif estimated_m < 15:
        return 32, 2
    elif estimated_m < 40:
        return 64, 1
    else:
        # Dense shapes: try block_m=64, split_k=1
        return 64, 1


def _fallback(data):
    """Standard fused_moe fallback."""
    from aiter.fused_moe import fused_moe
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


def _direct_cktile(data):
    """Direct cktile path with custom block_m/split_k."""
    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    bs = hidden_states.shape[0]
    d_hidden = config["d_hidden"]
    d_expert = config["d_expert"]
    d_hidden_pad = config["d_hidden_pad"]
    d_expert_pad = config["d_expert_pad"]
    topk = topk_ids.shape[1]
    num_experts = gate_up_weight_shuffled.shape[0]
    estimated_m = topk_ids.numel() // num_experts
    device = hidden_states.device

    block_m, split_k = _select_params(num_experts, estimated_m)
    hidden_pad = d_hidden_pad - d_hidden
    intermediate_pad = d_expert_pad - d_expert

    # Step 1: Token sorting
    total_tokens = bs * topk
    unit_size = block_m
    # Pad to multiple of (num_experts * unit_size) for alignment
    padded = (total_tokens + num_experts * unit_size - 1) // (num_experts * unit_size)
    padded_tokens = max(padded * num_experts * unit_size, total_tokens)

    sorted_token_ids = torch.empty(padded_tokens, dtype=torch.int32, device=device)
    sorted_weights = torch.empty(padded_tokens, dtype=torch.float32, device=device)
    sorted_expert_ids = torch.empty(
        padded_tokens // unit_size, dtype=torch.int32, device=device,
    )
    num_valid_ids = torch.empty(1, dtype=torch.int32, device=device)
    moe_buf = torch.empty(num_experts + 1, dtype=torch.int32, device=device)

    _sorting_fn(
        topk_ids, topk_weights,
        sorted_token_ids, sorted_weights, sorted_expert_ids,
        num_valid_ids, moe_buf,
        num_experts, unit_size,
    )

    # Step 2: Stage 1 — gate+up GEMM with SiLU
    # gate_up_weight_shuffled shape: [E, 2*d_expert_pad, d_hidden_pad//2] (fp4x2)
    intermediate_out = torch.empty(
        padded_tokens, d_expert_pad,
        dtype=torch.bfloat16, device=device,
    )

    _gemm1_fn(
        hidden_states,
        gate_up_weight_shuffled,
        intermediate_out,
        sorted_token_ids, sorted_expert_ids, num_valid_ids,
        topk,
        n_padded_zeros=hidden_pad,
        k_padded_zeros=0,
        topk_weight=None,
        x_scale=None,
        w_scale=gate_up_weight_scale_shuffled,
        activation=ActivationType.Silu.value,
        block_m=block_m,
        split_k=split_k,
    )

    # Step 3: Stage 2 — down GEMM
    output = torch.zeros(bs, d_hidden_pad, dtype=torch.bfloat16, device=device)

    _gemm2_fn(
        intermediate_out,
        down_weight_shuffled,
        output,
        sorted_token_ids, sorted_expert_ids, num_valid_ids,
        topk,
        n_padded_zeros=intermediate_pad,
        k_padded_zeros=0,
        topk_weight=sorted_weights,
        x_scale=None,
        w_scale=down_weight_scale_shuffled,
        activation=0,
        block_m=block_m,
        split_k=split_k,
    )

    # Trim hidden dimension padding
    if d_hidden_pad > d_hidden:
        output = output[:, :d_hidden]

    return output


def custom_kernel(data: input_t) -> output_t:
    _init()

    if _sorting_fn is None or _gemm1_fn is None or _gemm2_fn is None:
        return _fallback(data)

    try:
        return _direct_cktile(data)
    except Exception as e:
        print(f"DIRECT_CKTILE_ERR: {type(e).__name__}: {e}", file=sys.stderr)
        return _fallback(data)
