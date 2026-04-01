"""
GEMM Deep Probe: Read fused_mxfp4_quant module source to find the actual callable.
Also probe fused_flatten_mxfp4_quant and fused_rms_mxfp4_quant.
"""

from __future__ import annotations

import inspect
import os
import sys


os.environ["HIP_ONLINE_TUNING"] = "1"

from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    # === 1. Read fused_mxfp4_quant module source ===
    try:
        import aiter.ops.triton.quant.fused_mxfp4_quant as fmq

        src = inspect.getsource(fmq)
        print(f"fused_mxfp4_quant.py ({len(src)} chars):\n{src[:2000]}", file=sys.stderr)
        # List all callables in the module
        callables = [
            name for name in dir(fmq) if callable(getattr(fmq, name)) and not name.startswith("_")
        ]
        print(f"Callables in fused_mxfp4_quant: {callables}", file=sys.stderr)
    except Exception as e:
        print(f"fused_mxfp4_quant module read error: {e}", file=sys.stderr)

    # === 2. Read fused_flatten_mxfp4_quant module ===
    try:
        import aiter.ops.triton.quant.fused_flatten_mxfp4_quant as ffmq

        src = inspect.getsource(ffmq)
        print(f"fused_flatten_mxfp4_quant.py ({len(src)} chars):\n{src[:2000]}", file=sys.stderr)
        callables = [
            name for name in dir(ffmq) if callable(getattr(ffmq, name)) and not name.startswith("_")
        ]
        print(f"Callables in fused_flatten: {callables}", file=sys.stderr)
    except Exception as e:
        print(f"fused_flatten error: {e}", file=sys.stderr)

    # === 3. Read fused_rms_mxfp4_quant module ===
    try:
        import aiter.ops.triton.quant.fused_rms_mxfp4_quant as frmq

        src = inspect.getsource(frmq)
        print(f"fused_rms_mxfp4_quant.py ({len(src)} chars):\n{src[:1500]}", file=sys.stderr)
        callables = [
            name for name in dir(frmq) if callable(getattr(frmq, name)) and not name.startswith("_")
        ]
        print(f"Callables in fused_rms: {callables}", file=sys.stderr)
    except Exception as e:
        print(f"fused_rms error: {e}", file=sys.stderr)

    # === 4. Read dynamic_mxfp4_quant source for comparison ===
    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant

        src = inspect.getsource(dynamic_mxfp4_quant)
        print(f"dynamic_mxfp4_quant ({len(src)} chars):\n{src[:1000]}", file=sys.stderr)
    except Exception as e:
        print(f"dynamic_mxfp4_quant source error: {e}", file=sys.stderr)

    # === 5. List ALL .py files in aiter.ops.triton.quant ===
    try:
        import pathlib

        import aiter.ops.triton.quant as qpkg

        quant_dir = pathlib.Path(qpkg.__path__[0])
        py_files = sorted(quant_dir.glob("*.py"))
        print(f"quant package files ({len(py_files)}):", file=sys.stderr)
        for f in py_files:
            size = f.stat().st_size
            print(f"  {f.name} ({size} bytes)", file=sys.stderr)
    except Exception as e:
        print(f"quant dir listing error: {e}", file=sys.stderr)

    return ref_kernel(data)
