"""Probe: asm_moe — Hand-tuned assembly MoE kernel.

asm_moe is the highest-performance MoE kernel in AITER:
- Auto-dispatches based on quant type (BF16, A16W8, A8W8, INT8, FP8)
- Supports expert_mask natively
- Hand-tuned assembly for gfx942/gfx950

Key question: our weights are MXFP4 (fp4x2). Can asm_moe accept MXFP4 weights,
or does it need FP8/INT8? If it can't accept MXFP4 directly, can we re-quantize
to FP8 block-scaled and still pass correctness (rtol=2e-2)?

This probe:
1. Discovers asm_moe availability and signature
2. Tests if it can work with our MXFP4 weights (unlikely — may need FP8 re-quant)
3. Falls back to fused_moe if anything fails
"""

import inspect
import os
import sys


os.environ.setdefault("AITER_JIT_DIR", "/tmp/aiter_jit_cache")

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


# Fix JIT paths
_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Discovery Phase ──
_ASM_MOE = None
_ASM_MOE_SIG = ""

# Try importing asm_moe from known locations
for import_path in [
    "aiter.fused_moe_bf16_asm",
    "aiter.ops.moe_op",
    "aiter",
]:
    try:
        mod = __import__(import_path, fromlist=["asm_moe"])
        fn = getattr(mod, "asm_moe", None)
        if fn and callable(fn):
            _ASM_MOE = fn
            try:
                _ASM_MOE_SIG = str(inspect.signature(fn))
            except (ValueError, TypeError):
                _ASM_MOE_SIG = "signature unavailable"
            print(f"FOUND asm_moe from {import_path}: {_ASM_MOE_SIG}", file=sys.stderr)
            break
    except (ImportError, ModuleNotFoundError):
        continue

# Also discover asm_moe_tkw1 and ck_moe_2stages
for name in ("asm_moe_tkw1", "ck_moe_2stages", "moe_sorting_ck", "moe_sorting_opus"):
    for mod_path in ("aiter.fused_moe_bf16_asm", "aiter.ops.moe_op", "aiter"):
        try:
            mod = __import__(mod_path, fromlist=[name])
            fn = getattr(mod, name, None)
            if fn:
                try:
                    sig = str(inspect.signature(fn))
                except (ValueError, TypeError):
                    sig = "C++ binding"
                print(f"FOUND {name} from {mod_path}: {sig}", file=sys.stderr)
                break
        except (ImportError, ModuleNotFoundError):
            continue

# Discover fused_moe_dp_share_expert (DeepSeek-specific)
try:
    from aiter.fused_moe_dp_shared_expert import fused_moe_dp_share_expert
    try:
        sig = str(inspect.signature(fused_moe_dp_share_expert))
    except (ValueError, TypeError):
        sig = "C++ binding"
    print(f"FOUND fused_moe_dp_share_expert: {sig}", file=sys.stderr)
except (ImportError, ModuleNotFoundError):
    pass

# Check blockPerCu support in cktile
try:
    from aiter.ops.moe_op import moe_cktile2stages_gemm1
    try:
        sig = str(inspect.signature(moe_cktile2stages_gemm1))
    except (ValueError, TypeError):
        sig = "C++ binding"
    print(f"FOUND moe_cktile2stages_gemm1: {sig}", file=sys.stderr)
except (ImportError, ModuleNotFoundError):
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

    # Standard fused_moe — this probe is for DISCOVERY via stderr
    # A future submission would use asm_moe directly if compatible
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
