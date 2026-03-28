"""
MXFP4 MoE — Phase 12n: Probe asm_stage1 function signature.

Discovery: The MoE module has `asm_stage1` as a separate function.
This might be a different path than fmoe_int8_g1u0.

Dumps asm_stage1 signature/source to stderr, then falls back to
standard Phase 12j implementation.
"""
import sys
import os
import inspect
from task import input_t, output_t
from aiter.fused_moe import fused_moe
from aiter import ActivationType, QuantType

_probed = False


def _probe():
    global _probed
    if _probed:
        return
    _probed = True
    try:
        from aiter.fused_moe import asm_stage1
        sig = inspect.signature(asm_stage1)
        print(f"ASM_STAGE1_SIG: {sig}", file=sys.stderr)
        try:
            src = inspect.getsource(asm_stage1)
            print(f"ASM_STAGE1_SRC_LEN: {len(src)}", file=sys.stderr)
            print(src[:2000], file=sys.stderr)
        except (TypeError, OSError):
            print("ASM_STAGE1: no source (JIT)", file=sys.stderr)
    except ImportError:
        print("asm_stage1 not importable", file=sys.stderr)

    # Also probe fused_moe_1stage signature
    try:
        from aiter.fused_moe import fused_moe_1stage
        sig = inspect.signature(fused_moe_1stage)
        print(f"FUSED_MOE_1STAGE_SIG: {sig}", file=sys.stderr)
        try:
            src = inspect.getsource(fused_moe_1stage)
            print(f"FUSED_MOE_1STAGE_SRC_LEN: {len(src)}", file=sys.stderr)
            # Print lines containing fc2_smooth
            for i, line in enumerate(src.splitlines()):
                if "fc2_smooth" in line or "smooth" in line.lower():
                    print(f"  L{i}: {line.strip()}", file=sys.stderr)
        except (TypeError, OSError):
            print("FUSED_MOE_1STAGE: no source", file=sys.stderr)
    except ImportError:
        pass


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
