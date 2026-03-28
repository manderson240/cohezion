"""
MXFP4 MoE — Phase 12f: Try fused_moe_1stage directly.

The 1-stage probe revealed fused_moe_1stage exists as a separate function.
If it fuses gate_up+SiLU+down into a single kernel launch (vs 2-stage's
separate stage1+activation+stage2), it eliminates inter-stage buffer
allocation and 2 extra kernel launches.

Falls back to fused_moe on any error.
"""
import sys
import os
import inspect
from task import input_t, output_t
from aiter.fused_moe import fused_moe
from aiter import ActivationType, QuantType

_probed = False
_1stage_fn = None
_1stage_sig = None


def _probe_1stage():
    global _probed, _1stage_fn, _1stage_sig
    if _probed:
        return
    _probed = True
    try:
        from aiter.fused_moe import fused_moe_1stage
        _1stage_fn = fused_moe_1stage
        try:
            _1stage_sig = inspect.signature(fused_moe_1stage)
            print(f"FUSED_MOE_1STAGE_SIG: {_1stage_sig}", file=sys.stderr)
            src = inspect.getsource(fused_moe_1stage)
            print(f"FUSED_MOE_1STAGE_SRC ({len(src)} chars):", file=sys.stderr)
            print(src[:4000], file=sys.stderr)
        except Exception as e:
            print(f"1STAGE_SIG_ERR: {e}", file=sys.stderr)
    except ImportError:
        print("fused_moe_1stage not importable", file=sys.stderr)
    except Exception as e:
        print(f"1STAGE_PROBE_ERR: {e}", file=sys.stderr)


def custom_kernel(data: input_t) -> output_t:
    _probe_1stage()

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

    # Try 1-stage for dense shapes where it might have advantage
    if _1stage_fn is not None and estimated_m >= 50:
        try:
            return _1stage_fn(
                hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
                topk_weights, topk_ids, expert_mask=None,
                activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
                w1_scale=gate_up_weight_scale_shuffled,
                w2_scale=down_weight_scale_shuffled,
                a1_scale=None, a2_scale=None,
                hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
            )
        except Exception as e:
            print(f"1STAGE_CALL_ERR: {e}", file=sys.stderr)

    # Fallback: standard 2-stage with adaptive routing
    if estimated_m >= 50:
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
        doweight = True
    elif num_experts >= 200 and estimated_m < 10:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "4"
        doweight = False
    else:
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
        doweight = False

    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids, expert_mask=None,
        activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
        doweight_stage1=doweight,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hidden_pad, intermediate_pad=intermediate_pad,
    )
