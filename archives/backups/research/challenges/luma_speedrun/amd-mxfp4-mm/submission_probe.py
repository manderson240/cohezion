#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM probe: discover runner APIs, .co files, tuning configs, headers."""

import glob
import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


print("=== RUNNER PROBE v2 ===")
print(f"torch: {torch.__version__}, hip: {getattr(torch.version, 'hip', 'N/A')}")
print(f"aiter: {aiter.__file__}")

# All aiter public callables
print("\n=== AITER CALLABLES ===")
for x in sorted(dir(aiter)):
    obj = getattr(aiter, x, None)
    if callable(obj) and not x.startswith("_"):
        print(f"  aiter.{x}")

# GEMM-specific
print("\n=== GEMM FUNCTIONS (detailed) ===")
for name in [
    "gemm_a4w4",
    "gemm_afp4wfp4",
    "gemm_a4w4_blockscale",
    "gemm_a4w4_asm",
    "matmul",
    "linear",
    "gemm_fp8",
    "gemm_a16w4",
    "gemm_a16w8",
]:
    fn = getattr(aiter, name, None)
    if fn:
        try:
            import inspect

            sig = inspect.signature(fn)
            print(f"  aiter.{name}{sig}")
        except Exception:
            print(f"  aiter.{name}: EXISTS")

# fused_moe
print("\n=== FUSED_MOE ===")
try:
    import inspect

    from aiter.fused_moe import fused_moe as _fm

    print(f"  fused_moe{inspect.signature(_fm)}")
except Exception as e:
    print(f"  Error: {e}")
for name in ["asm_moe", "fmoe_g1u1", "moe_sorting_fwd", "moe_sorting_dispatch_policy"]:
    try:
        from aiter import fused_moe as fm_mod

        fn = getattr(fm_mod, name, None)
        print(f"  fused_moe.{name}: {'EXISTS' if fn else 'NOT FOUND'}")
    except Exception:
        pass

# MLA
print("\n=== MLA ===")
try:
    from aiter import mla

    for x in sorted(dir(mla)):
        if not x.startswith("_") and callable(getattr(mla, x, None)):
            print(f"  mla.{x}")
except Exception as e:
    print(f"  Error: {e}")

# .co kernel files
print("\n=== .co FILES ===")
for d in [
    "/home/runner/aiter/hsa/gfx950/f4gemm",
    "/home/runner/aiter/hsa/gfx950/mla",
    "/home/runner/aiter/hsa/gfx950/fmoe_2stages",
    "/home/runner/aiter/hsa/gfx950",
]:
    files = glob.glob(f"{d}/*.co") if os.path.isdir(d) else []
    if files:
        print(f"  {d}/: {len(files)} files")
        for f in sorted(files)[:5]:
            print(f"    {os.path.basename(f)}")
        if len(files) > 5:
            print(f"    ... +{len(files) - 5} more")

# Tuning CSVs
print("\n=== TUNING ===")
for pat in ["/home/runner/aiter/**/*.csv"]:
    files = glob.glob(pat, recursive=True)
    for f in files[:8]:
        sz = os.path.getsize(f)
        print(f"  {f} ({sz}B)")
        try:
            with open(f) as fh:
                lines = fh.readlines()
                print(f"    header: {lines[0].strip()[:120]}")
                if len(lines) > 1:
                    print(f"    row1: {lines[1].strip()[:120]}")
                print(f"    rows: {len(lines)}")
        except Exception:
            pass

# Headers
print("\n=== HEADERS ===")
for h in ["/opt/rocm/include/hip/hip_ext_ocp.h", "/opt/rocm/include/hip/amd_detail/amd_hip_fp8.h"]:
    exists = os.path.exists(h)
    print(f"  {os.path.basename(h)}: {'YES' if exists else 'NO'}")
    if exists:
        try:
            with open(h) as fh:
                content = fh.read()
                # Find MFMA-related functions
                for line in content.split("\n"):
                    if "mfma" in line.lower() and ("f4" in line or "f6" in line or "scale" in line):
                        print(f"    {line.strip()[:120]}")
        except Exception:
            pass

# tritonblas
print("\n=== TRITONBLAS ===")
try:
    import tritonblas

    print(f"  path: {tritonblas.__file__}")
    funcs = [x for x in dir(tritonblas) if not x.startswith("_")]
    print(f"  funcs: {funcs[:15]}")
except ImportError:
    print("  NOT AVAILABLE")

# Check for env vars that affect aiter
print("\n=== AITER ENV ===")
for v in [
    "AITER_USE_NT",
    "AITER_KSPLIT",
    "AITER_BYPASS_TUNE_CONFIG",
    "AITER_JIT_DIR",
    "AITER_MLA_USE_PERSISTENT",
]:
    print(f"  {v}={os.environ.get(v, '<unset>')}")

print("\n=== END PROBE ===")


# Working kernel (correctness fallback)
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
