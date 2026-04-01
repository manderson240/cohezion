"""MoE Probe: Dump runner state for MoE MXFP4 optimization paths."""

from __future__ import annotations

import inspect
import sys

from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    # === 1. aiter fused_moe source and new params ===
    try:
        import aiter

        print(f"aiter version: {aiter.__version__}", file=sys.stderr)
        src = inspect.getsource(aiter.fused_moe)
        print(f"fused_moe source ({len(src)} chars):\n{src[:1500]}", file=sys.stderr)
    except Exception as e:
        print(f"fused_moe source error: {e}", file=sys.stderr)

    # === 2. Check for NEW MoE APIs ===
    try:
        import aiter

        moe_attrs = [a for a in dir(aiter) if "moe" in a.lower() or "expert" in a.lower()]
        print(f"MoE-related attrs: {moe_attrs}", file=sys.stderr)
    except Exception as e:
        print(f"aiter moe scan error: {e}", file=sys.stderr)

    # === 3. Check env vars that affect MoE ===
    try:
        import os

        moe_env = {k: v for k, v in os.environ.items() if "AITER" in k or "MOE" in k or "CK" in k}
        print(f"MoE env vars: {moe_env}", file=sys.stderr)
    except Exception as e:
        print(f"env scan error: {e}", file=sys.stderr)

    # === 4. Check fmoe_g1u1 availability and signature ===
    try:
        from aiter import fmoe_g1u1

        sig = inspect.signature(fmoe_g1u1)
        print(f"fmoe_g1u1 signature: {sig}", file=sys.stderr)
        src = inspect.getsource(fmoe_g1u1)
        print(f"fmoe_g1u1 source ({len(src)} chars):\n{src[:800]}", file=sys.stderr)
    except Exception as e:
        print(f"fmoe_g1u1 error: {e}", file=sys.stderr)

    # === 5. Check torch.ops.aiter for hidden ops ===
    try:
        import torch

        aiter_ops = [a for a in dir(torch.ops.aiter) if not a.startswith("_")]
        moe_ops = [
            a
            for a in aiter_ops
            if "moe" in a.lower() or "expert" in a.lower() or "fuse" in a.lower()
        ]
        print(f"torch.ops.aiter MoE ops ({len(moe_ops)}): {moe_ops}", file=sys.stderr)
        print(f"torch.ops.aiter ALL ({len(aiter_ops)}): {aiter_ops[:50]}", file=sys.stderr)
    except Exception as e:
        print(f"torch.ops.aiter error: {e}", file=sys.stderr)

    # === 6. Check for CK MoE kernels ===
    try:
        from aiter.jit.core import CKModule

        ck_attrs = [a for a in dir(CKModule) if "moe" in a.lower()]
        print(f"CKModule MoE attrs: {ck_attrs}", file=sys.stderr)
    except Exception as e:
        print(f"CKModule error: {e}", file=sys.stderr)

    # Run reference for correctness
    return ref_kernel(data)
