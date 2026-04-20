"""
GEMM Novel Approach: Use aiter.tuned_gemm.tgemm.mm() — a completely different API path.

From AITER blog: tuned_gemm provides auto-tuned GEMM via CK/hipBLASLt.
This is different from gemm_a4w4 (ASM kernel) and tritonblas.matmul_fp4 (Triton).
If tuned_gemm supports fp4 input, it could have different performance characteristics.

Also test: VLLM_USE_AITER_BLOCK_GEMM=1 environment variable.
"""

from __future__ import annotations

import inspect
import os
import sys


os.environ["HIP_ONLINE_TUNING"] = "1"
os.environ["VLLM_USE_AITER_BLOCK_GEMM"] = "1"

import aiter
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]

    # === Probe 1: tuned_gemm API tree ===
    try:
        from aiter import tuned_gemm

        attrs = [a for a in dir(tuned_gemm) if not a.startswith("_")]
        print(f"tuned_gemm attrs: {attrs}", file=sys.stderr)

        if hasattr(tuned_gemm, "tgemm"):
            tg = tuned_gemm.tgemm
            tg_attrs = [a for a in dir(tg) if not a.startswith("_")]
            print(f"tgemm attrs: {tg_attrs}", file=sys.stderr)

            if hasattr(tg, "mm"):
                sig = str(inspect.signature(tg.mm))
                print(f"tgemm.mm signature: {sig}", file=sys.stderr)

                # Try with bf16 inputs (baseline comparison)
                try:
                    out_bf16 = tg.mm(A, B.t())
                    print(f"tgemm.mm bf16 SUCCESS: {out_bf16.shape}", file=sys.stderr)
                except Exception as e:
                    print(f"tgemm.mm bf16 failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"tuned_gemm error: {e}", file=sys.stderr)

    # === Probe 2: Block GEMM API (from VLLM_USE_AITER_BLOCK_GEMM) ===
    try:
        block_gemm_attrs = [a for a in dir(aiter) if "block" in a.lower() and "gemm" in a.lower()]
        print(f"block_gemm attrs: {block_gemm_attrs}", file=sys.stderr)

        for attr_name in block_gemm_attrs:
            fn = getattr(aiter, attr_name)
            if callable(fn):
                sig = str(inspect.signature(fn))
                print(f"  {attr_name} sig: {sig}", file=sys.stderr)
    except Exception as e:
        print(f"block_gemm scan: {e}", file=sys.stderr)

    # === Probe 3: All GEMM-related ops in torch.ops.aiter ===
    try:
        import torch

        ops = [a for a in dir(torch.ops.aiter) if "gemm" in a.lower() or "mm" in a.lower()]
        print(f"torch.ops.aiter GEMM ops: {ops}", file=sys.stderr)
    except Exception as e:
        print(f"ops scan: {e}", file=sys.stderr)

    # === Probe 4: hipblaslt availability on runner ===
    try:
        import hipblas  # noqa: F401

        print("hipblas available!", file=sys.stderr)
    except ImportError:
        print("hipblas: NOT available", file=sys.stderr)

    try:
        import hipblaslt  # noqa: F401

        print("hipblaslt available!", file=sys.stderr)
        hb_attrs = [a for a in dir(hipblaslt) if not a.startswith("_")]
        print(f"hipblaslt attrs: {hb_attrs[:20]}", file=sys.stderr)
    except ImportError:
        print("hipblaslt: NOT available", file=sys.stderr)

    return ref_kernel(data)
