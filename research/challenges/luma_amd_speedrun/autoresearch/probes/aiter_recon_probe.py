"""Aiter Reconnaissance Probe.

PURPOSE: Discover all available functions, kernel variants, and undocumented
parameters in the aiter library on the MI355X runner. Submit as any kernel's
submission.py to get a dump of the aiter API surface.

Output goes to stderr (visible in popcorn-cli output).
"""

# This probe works for GEMM — submit as kernels/mxfp4-mm/submission.py
PROBE_SUBMISSION_GEMM = """\
import sys, torch
from task import input_t, output_t
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle

_probed = False

def custom_kernel(data: input_t) -> output_t:
    global _probed
    A, B, B_q, B_shuffle, B_scale_sh = data

    if not _probed:
        _probed = True
        print("[RECON] === aiter module contents ===", file=sys.stderr)
        for name in sorted(dir(aiter)):
            obj = getattr(aiter, name, None)
            if callable(obj) and not name.startswith("_"):
                print(f"[RECON] aiter.{name}: {type(obj).__name__}", file=sys.stderr)

        # Check for ASM/CK kernel variants
        print("[RECON] === gemm variants ===", file=sys.stderr)
        for name in sorted(dir(aiter)):
            if "gemm" in name.lower():
                obj = getattr(aiter, name, None)
                print(f"[RECON] aiter.{name}", file=sys.stderr)
                # Try to get signature
                try:
                    import inspect
                    sig = inspect.signature(obj)
                    print(f"[RECON]   params: {sig}", file=sys.stderr)
                except:
                    pass

        # Check for MLA variants
        print("[RECON] === MLA modules ===", file=sys.stderr)
        try:
            from aiter import mla
            for name in sorted(dir(mla)):
                if not name.startswith("_"):
                    print(f"[RECON] aiter.mla.{name}", file=sys.stderr)
        except Exception as e:
            print(f"[RECON] aiter.mla import failed: {e}", file=sys.stderr)

        # Check for fused_moe variants
        print("[RECON] === fused_moe ===", file=sys.stderr)
        try:
            from aiter.fused_moe import fused_moe
            import inspect
            sig = inspect.signature(fused_moe)
            print(f"[RECON] fused_moe params: {sig}", file=sys.stderr)
        except Exception as e:
            print(f"[RECON] fused_moe inspect failed: {e}", file=sys.stderr)

        # Check for quant variants
        print("[RECON] === quant functions ===", file=sys.stderr)
        try:
            from aiter.ops.triton import quant
            for name in sorted(dir(quant)):
                if not name.startswith("_"):
                    print(f"[RECON] aiter.ops.triton.quant.{name}", file=sys.stderr)
        except Exception as e:
            print(f"[RECON] quant module failed: {e}", file=sys.stderr)

        # Check aiter version
        print(f"[RECON] aiter version: {getattr(aiter, '__version__', 'unknown')}", file=sys.stderr)

        # Check env vars that aiter reads
        print("[RECON] === env var check ===", file=sys.stderr)
        import os
        for var in ["AITER_KSPLIT", "AITER_BYPASS_TUNE_CONFIG", "AITER_USE_NT",
                     "AITER_MLA_USE_PERSISTENT", "AITER_JIT_DIR", "AITER_USE_OPUS_MOE_SORTING"]:
            val = os.environ.get(var, "NOT SET")
            print(f"[RECON] {var}={val}", file=sys.stderr)

    # Normal execution for correctness
    A = A.contiguous()
    A_q_raw, A_scale_raw = dynamic_mxfp4_quant(A)
    A_scale_shuffled = e8m0_shuffle(A_scale_raw).view(dtypes.fp8_e8m0)
    A_q = A_q_raw.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(A_q, B_shuffle, A_scale_shuffled, B_scale_sh,
                           dtype=dtypes.bf16, bpreshuffle=True)
"""
