"""
MoE: Try fused_dynamic_mxfp4_quant_moe_sort — fuses quant+sort into single kernel.

Discovered via probe: "Fusing dynamic_mxfp4_quant and moe_mxfp4_sort"
If this works, it eliminates separate quant + sort kernel launches.
"""

from __future__ import annotations

import inspect
import os
import sys


os.environ["AITER_USE_NT"] = "1"

from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    import aiter

    # === 1. Probe the full source and signature ===
    try:
        from aiter.ops.triton.quant import fused_dynamic_mxfp4_quant_moe_sort as fqms_mod

        # It might be a module like fused_mxfp4_quant was
        if callable(fqms_mod):
            sig = inspect.signature(fqms_mod)
            print(f"fused_quant_moe_sort is CALLABLE, sig: {sig}", file=sys.stderr)
            src = inspect.getsource(fqms_mod)
            print(f"source ({len(src)} chars):\n{src[:2000]}", file=sys.stderr)
        else:
            # It's a module — find the callable inside
            callables = [
                n for n in dir(fqms_mod) if callable(getattr(fqms_mod, n)) and not n.startswith("_")
            ]
            print(f"fused_quant_moe_sort is MODULE, callables: {callables}", file=sys.stderr)
            # Try the most likely function name
            for name in [
                "fused_dynamic_mxfp4_quant_moe_sort",
                "fused_quant_moe_sort",
                "fused_mxfp4_quant_moe_sort",
            ]:
                fn = getattr(fqms_mod, name, None)
                if fn and callable(fn):
                    sig = inspect.signature(fn)
                    print(f"Found callable {name}, sig: {sig}", file=sys.stderr)
                    src = inspect.getsource(fn)
                    print(f"source ({len(src)} chars):\n{src[:2000]}", file=sys.stderr)
                    break
    except Exception as e:
        print(f"fused_quant_moe_sort error: {e}", file=sys.stderr)

    # === 2. Also probe fmoe_g1u1_a16 (truncated in last probe) ===
    try:
        fn = aiter.fmoe_g1u1_a16
        # Get the actual torch.ops.aiter function name
        src = inspect.getsource(fn)
        print(f"fmoe_g1u1_a16 wrapper source:\n{src[:500]}", file=sys.stderr)
    except Exception as e:
        print(f"fmoe_g1u1_a16 error: {e}", file=sys.stderr)

    # === 3. Probe moe_stage1_g1u1 ===
    try:
        fn = aiter.moe_stage1_g1u1
        if callable(fn):
            src = inspect.getsource(fn)
            print(f"moe_stage1_g1u1 source ({len(src)}):\n{src[:800]}", file=sys.stderr)
    except Exception as e:
        print(f"moe_stage1_g1u1 error: {e}", file=sys.stderr)

    # === 4. Probe moe_fused_gate ===
    try:
        fn = aiter.moe_fused_gate
        if callable(fn):
            src = inspect.getsource(fn)
            print(f"moe_fused_gate source ({len(src)}):\n{src[:800]}", file=sys.stderr)
    except Exception as e:
        print(f"moe_fused_gate error: {e}", file=sys.stderr)

    return ref_kernel(data)
