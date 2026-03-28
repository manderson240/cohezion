"""
MXFP4 MoE — Phase 12c: Probe fused_moe_ for 1-stage kernel path.

Introspects fused_moe_ to find:
1. run_1stage parameter or equivalent
2. How cktile_moe_gemm1/gemm2 are called
3. Whether fmoe_g1u1 can be called directly

Falls back to doweight_stage1=True for actual computation.
Probe output goes to stderr only on first call.
"""
import sys
import os
import inspect
from task import input_t, output_t
from aiter.fused_moe import fused_moe
from aiter import ActivationType, QuantType

_probed = False


def _probe_once():
    global _probed
    if _probed:
        return
    _probed = True
    try:
        from aiter import fused_moe as fmoe_module

        # List all functions in the module
        funcs = [n for n in dir(fmoe_module)
                 if not n.startswith('_') and callable(getattr(fmoe_module, n, None))]
        print(f"MOE_MODULE_FUNCS: {funcs}", file=sys.stderr)

        # Get fused_moe_ inner function
        fmoe_inner = getattr(fmoe_module, 'fused_moe_', None)
        if fmoe_inner:
            sig = inspect.signature(fmoe_inner)
            print(f"FUSED_MOE_INNER_SIG: {sig}", file=sys.stderr)
            # Get first 6000 chars of source
            src = inspect.getsource(fmoe_inner)
            # Look for key patterns
            for pattern in ['run_1stage', '1stage', 'g1u1', 'fmoe_g1u1',
                          'block_size_M', 'block_m', 'split_k', 'splitk',
                          'non_temporal', 'cktile', 'ck_moe']:
                lines = [l.strip() for l in src.split('\n') if pattern in l.lower()]
                if lines:
                    print(f"PATTERN[{pattern}]: {lines[:5]}", file=sys.stderr)

            # Print full source (first 8000 chars)
            print(f"FUSED_MOE_INNER_SRC_LEN: {len(src)}", file=sys.stderr)
            print(src[:8000], file=sys.stderr)

        # Check for g1u1 path
        g1u1 = getattr(fmoe_module, 'fmoe_g1u1', None)
        if g1u1:
            try:
                g1u1_sig = inspect.signature(g1u1)
                print(f"FMOE_G1U1_SIG: {g1u1_sig}", file=sys.stderr)
            except Exception:
                print("FMOE_G1U1: exists but no signature", file=sys.stderr)

        # Check for get_2stage_cfgs
        get_cfgs = getattr(fmoe_module, 'get_2stage_cfgs', None)
        if get_cfgs:
            try:
                cfgs_src = inspect.getsource(get_cfgs)
                print(f"GET_2STAGE_CFGS:\n{cfgs_src[:3000]}", file=sys.stderr)
            except Exception:
                print("GET_2STAGE_CFGS: exists but no source", file=sys.stderr)

    except Exception as e:
        print(f"PROBE_ERROR: {e}", file=sys.stderr)


def custom_kernel(data: input_t) -> output_t:
    _probe_once()

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
        doweight_stage1=True,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
    )
