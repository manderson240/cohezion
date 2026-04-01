"""Probe: fmoe_fp8_blockscale_g1u1 — Block-scaled FP8 MoE kernel.

This kernel is disabled by default in vLLM (VLLM_ROCM_USE_AITER_FP8_BLOCK_SCALED_MOE).
It uses FP8 block quantization instead of MXFP4. The question is:
1. Is it available on the runner?
2. What's its signature?
3. Can it produce correct results against the MXFP4 reference?
4. Is it faster than fused_moe with MXFP4?

Strategy: Use inspect to discover the signature, then call with our data.
The weights are MXFP4 but the kernel may need FP8 — we'd need to re-quantize.
"""

import inspect
import os
import sys


os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")

import aiter
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Discovery: find fmoe_fp8_blockscale_g1u1
_DISCOVERED = False
_FP8_BLOCKSCALE = None

try:
    from aiter.moe_op import fmoe_fp8_blockscale_g1u1
    _FP8_BLOCKSCALE = fmoe_fp8_blockscale_g1u1
    _DISCOVERED = True
    print(f"FOUND fmoe_fp8_blockscale_g1u1: {inspect.signature(fmoe_fp8_blockscale_g1u1)}", file=sys.stderr)
except ImportError:
    pass

if not _DISCOVERED:
    try:
        _FP8_BLOCKSCALE = getattr(aiter, "fmoe_fp8_blockscale_g1u1", None)
        if _FP8_BLOCKSCALE:
            _DISCOVERED = True
            print(f"FOUND via aiter: {inspect.signature(_FP8_BLOCKSCALE)}", file=sys.stderr)
    except Exception:
        pass

if not _DISCOVERED:
    # Also check fmoe_g1u1_tkw1 and fmoe_g1u1_a16 while we're at it
    for name in ("fmoe_g1u1_tkw1", "fmoe_g1u1_a16", "moe_stage1_g1u1"):
        try:
            fn = getattr(aiter, name, None) or getattr(aiter.moe_op, name, None)
            if fn:
                print(f"FOUND {name}: {inspect.signature(fn)}", file=sys.stderr)
        except Exception as e:
            print(f"PROBE {name}: {e}", file=sys.stderr)


# Fix sys.path for JIT builds
_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)


def custom_kernel(data: input_t) -> output_t:
    """Fallback to fused_moe if probe kernel unavailable."""
    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]

    # Always fall back to fused_moe — the probe is for DISCOVERY only
    # On the runner, stderr will show the discovered signatures
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
