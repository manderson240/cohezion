"""GEMM Probe: Dump runner state for MXFP4 GEMM optimization paths."""

from __future__ import annotations

import inspect
import sys

from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    # === 1. aiter version and gemm APIs ===
    try:
        import aiter

        print(f"aiter version: {aiter.__version__}", file=sys.stderr)
        gemm_attrs = [
            a for a in dir(aiter) if "gemm" in a.lower() or "mm" in a.lower() or "fp4" in a.lower()
        ]
        print(f"GEMM-related attrs: {gemm_attrs}", file=sys.stderr)
    except Exception as e:
        print(f"aiter import error: {e}", file=sys.stderr)

    # === 2. tritonblas APIs ===
    try:
        import tritonblas

        print(
            f"tritonblas version: {getattr(tritonblas, '__version__', 'unknown')}", file=sys.stderr
        )
        tb_attrs = [a for a in dir(tritonblas) if not a.startswith("_")]
        print(f"tritonblas exports: {tb_attrs}", file=sys.stderr)

        # Check if fp4_matmul kernel source is accessible
        from tritonblas import matmul_fp4

        src = inspect.getsource(matmul_fp4)
        print(f"matmul_fp4 source length: {len(src)} chars", file=sys.stderr)
        # Print first 500 chars of the wrapper
        print(f"matmul_fp4 wrapper:\n{src[:500]}", file=sys.stderr)
    except Exception as e:
        print(f"tritonblas error: {e}", file=sys.stderr)

    # === 3. Check for fp4_matmul Triton kernel source ===
    try:
        from tritonblas.fp4_matmul import fp4_matmul as _kernel

        ksrc = inspect.getsource(_kernel.fn)
        print(f"fp4_matmul kernel source length: {len(ksrc)} chars", file=sys.stderr)
        print(f"fp4_matmul kernel (first 800):\n{ksrc[:800]}", file=sys.stderr)
    except Exception as e:
        print(f"fp4_matmul kernel access error: {e}", file=sys.stderr)
        # Try alternate import paths
        try:
            import tritonblas.fp4_matmul as fp4mod

            fp4_attrs = [a for a in dir(fp4mod) if not a.startswith("_")]
            print(f"fp4_matmul module attrs: {fp4_attrs}", file=sys.stderr)
        except Exception as e2:
            print(f"fp4_matmul module error: {e2}", file=sys.stderr)

    # === 4. Check for NEW aiter quant methods ===
    try:
        from aiter.ops.triton import quant as qmod

        quant_attrs = [a for a in dir(qmod) if not a.startswith("_")]
        print(f"aiter quant exports: {quant_attrs}", file=sys.stderr)
    except Exception as e:
        print(f"aiter quant error: {e}", file=sys.stderr)

    # === 5. Check Triton version and type registry ===
    try:
        import triton

        print(f"triton version: {triton.__version__}", file=sys.stderr)
        # Check if float4 types exist
        import triton.language as tl

        float_types = [a for a in dir(tl) if "float" in a.lower() or "fp" in a.lower()]
        print(f"triton float types: {float_types}", file=sys.stderr)
    except Exception as e:
        print(f"triton error: {e}", file=sys.stderr)

    # === 6. Check torch MXFP4 ops ===
    try:
        import torch

        scaled_mm_attrs = [a for a in dir(torch) if "scaled" in a.lower() or "fp4" in a.lower()]
        print(f"torch scaled/fp4 attrs: {scaled_mm_attrs}", file=sys.stderr)
        # Check _C for native ops
        native_fp4 = [a for a in dir(torch._C) if "fp4" in a.lower() or "mxfp" in a.lower()]
        print(f"torch._C fp4 attrs: {native_fp4}", file=sys.stderr)
    except Exception as e:
        print(f"torch error: {e}", file=sys.stderr)

    # Run reference for correctness
    return ref_kernel(data)
