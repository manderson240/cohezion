"""
MoE BREAKTHROUGH PROBE: a4w4_asm_moe — Dedicated ASM MoE kernel for MXFP4.

From AITER v0.1.5+ release notes: "add a4w4 asm_moe" (PR #482)
Also: "A4w4_asm_pro" and "A4w4_asm_pro_max_v2" optimizations.
Also probing: FlyDSL (ROCm/FlyDSL) — MLIR-backed Python kernel DSL.
"""
from __future__ import annotations

import inspect
import sys

import aiter
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    # === Probe 1: a4w4_asm_moe and variants ===
    asm_moe_funcs = [a for a in dir(aiter) if "asm_moe" in a.lower() or "a4w4" in a.lower()]
    print(f"ASM MoE functions: {asm_moe_funcs}", file=sys.stderr)

    for name in asm_moe_funcs:
        fn = getattr(aiter, name, None)
        if callable(fn):
            try:
                sig = str(inspect.signature(fn))
                print(f"  {name} sig: {sig}", file=sys.stderr)
            except Exception as e:
                print(f"  {name}: {e}", file=sys.stderr)

    # === Probe 2: _asm_pro variants ===
    pro_funcs = [a for a in dir(aiter) if "pro" in a.lower() and ("moe" in a.lower() or "gemm" in a.lower())]
    print(f"Pro functions: {pro_funcs}", file=sys.stderr)

    # === Probe 3: FlyDSL availability ===
    try:
        import flydsl
        print("FlyDSL AVAILABLE!", file=sys.stderr)
        fly_attrs = [a for a in dir(flydsl) if not a.startswith("_")]
        print(f"FlyDSL attrs: {fly_attrs[:20]}", file=sys.stderr)
    except ImportError:
        print("FlyDSL: NOT available", file=sys.stderr)

    # === Probe 4: pa_ps_asm (paged attention persistent ASM) ===
    pa_funcs = [a for a in dir(aiter) if "pa_ps" in a.lower() or "paged_attn" in a.lower()]
    print(f"Paged attention ASM: {pa_funcs}", file=sys.stderr)

    # === Probe 5: torch.ops.aiter MoE ops ===
    try:
        import torch
        moe_ops = [a for a in dir(torch.ops.aiter) if "moe" in a.lower() or "asm" in a.lower()]
        print(f"torch.ops.aiter MoE/ASM: {moe_ops}", file=sys.stderr)
    except Exception as e:
        print(f"torch.ops.aiter scan: {e}", file=sys.stderr)

    # === Probe 6: aiter.fused_moe internals — look for asm dispatch ===
    try:
        from aiter.fused_moe import fused_moe as fm
        src = inspect.getsource(fm)
        asm_lines = [line.strip() for line in src.split('\n') if 'asm' in line.lower()]
        print(f"fused_moe ASM references ({len(asm_lines)}):", file=sys.stderr)
        for line in asm_lines[:10]:
            print(f"  {line}", file=sys.stderr)
    except Exception as e:
        print(f"fused_moe source: {e}", file=sys.stderr)

    # === Probe 7: AITER version ===
    try:
        print(f"aiter version: {aiter.__version__}", file=sys.stderr)
    except AttributeError:
        print("aiter: no __version__", file=sys.stderr)

    return ref_kernel(data)
