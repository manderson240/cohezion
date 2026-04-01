"""
MoE: Probe new aiter APIs discovered in Session 76.

Tests fmoe_g1u1_a16 and moe_stage1_g1u1 signatures.
Falls back to ref_kernel for correctness.
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

    # === 1. fmoe_g1u1_a16 — A16 variant (might fix NaN) ===
    try:
        sig_str = str(inspect.signature(aiter.fmoe_g1u1_a16))
        print(f"fmoe_g1u1_a16 signature: {sig_str}", file=sys.stderr)
        src = inspect.getsource(aiter.fmoe_g1u1_a16)
        print(f"fmoe_g1u1_a16 source ({len(src)} chars):\n{src[:600]}", file=sys.stderr)
    except Exception as e:
        print(f"fmoe_g1u1_a16 error: {e}", file=sys.stderr)

    # === 2. fmoe_g1u1_tkw1 — token-K-weight variant ===
    try:
        sig_str = str(inspect.signature(aiter.fmoe_g1u1_tkw1))
        print(f"fmoe_g1u1_tkw1 signature: {sig_str}", file=sys.stderr)
        src = inspect.getsource(aiter.fmoe_g1u1_tkw1)
        print(f"fmoe_g1u1_tkw1 source ({len(src)} chars):\n{src[:600]}", file=sys.stderr)
    except Exception as e:
        print(f"fmoe_g1u1_tkw1 error: {e}", file=sys.stderr)

    # === 3. moe_stage1_g1u1 — direct stage1 ===
    try:
        sig_str = str(inspect.signature(aiter.moe_stage1_g1u1))
        print(f"moe_stage1_g1u1 signature: {sig_str}", file=sys.stderr)
        src = inspect.getsource(aiter.moe_stage1_g1u1)
        print(f"moe_stage1_g1u1 source ({len(src)} chars):\n{src[:600]}", file=sys.stderr)
    except Exception as e:
        print(f"moe_stage1_g1u1 error: {e}", file=sys.stderr)

    # === 4. moe_cktile2stages_gemm1_ck — direct CK GEMM1 ===
    try:
        sig_str = str(inspect.signature(aiter.moe_cktile2stages_gemm1_ck))
        print(f"moe_cktile2stages_gemm1_ck signature: {sig_str}", file=sys.stderr)
    except Exception as e:
        print(f"moe_cktile2stages_gemm1_ck error: {e}", file=sys.stderr)

    # === 5. moe_fused_gate — gating ===
    try:
        sig_str = str(inspect.signature(aiter.moe_fused_gate))
        print(f"moe_fused_gate signature: {sig_str}", file=sys.stderr)
    except Exception as e:
        print(f"moe_fused_gate error: {e}", file=sys.stderr)

    # === 6. fused_dynamic_mxfp4_quant_moe_sort — FUSED quant+sort ===
    try:
        from aiter.ops.triton.quant import fused_dynamic_mxfp4_quant_moe_sort

        sig_str = str(inspect.signature(fused_dynamic_mxfp4_quant_moe_sort))
        print(f"fused_dynamic_mxfp4_quant_moe_sort sig: {sig_str}", file=sys.stderr)
        src = inspect.getsource(fused_dynamic_mxfp4_quant_moe_sort)
        print(f"fused_quant_moe_sort source ({len(src)} chars):\n{src[:800]}", file=sys.stderr)
    except Exception as e:
        print(f"fused_dynamic_mxfp4_quant_moe_sort error: {e}", file=sys.stderr)

    # === 7. fmoe (base function) ===
    try:
        sig_str = str(inspect.signature(aiter.fmoe))
        print(f"fmoe signature: {sig_str}", file=sys.stderr)
    except Exception as e:
        print(f"fmoe error: {e}", file=sys.stderr)

    return ref_kernel(data)
