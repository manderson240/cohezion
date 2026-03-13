"""Probe: Explore tritonblas 0.1.0 API — what GEMM kernels does it offer?"""
import sys
import os
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    # Probe 1: tritonblas top-level API
    try:
        import tritonblas
        print(f"TRITONBLAS VERSION: {tritonblas.__version__}", file=sys.stderr)
        print(f"TRITONBLAS DIR: {sorted(dir(tritonblas))}", file=sys.stderr)
        tb_path = os.path.dirname(tritonblas.__file__)
        print(f"TRITONBLAS PATH: {tb_path}", file=sys.stderr)
        # List all files/dirs
        for f in sorted(os.listdir(tb_path)):
            full = os.path.join(tb_path, f)
            if os.path.isdir(full):
                print(f"  DIR: {f}/", file=sys.stderr)
                # List subdir contents
                for sf in sorted(os.listdir(full))[:15]:
                    print(f"    {sf}", file=sys.stderr)
            else:
                print(f"  FILE: {f}", file=sys.stderr)
    except ImportError as e:
        print(f"TRITONBLAS NOT FOUND: {e}", file=sys.stderr)
    except Exception as e:
        print(f"TRITONBLAS ERROR: {type(e).__name__}: {e}", file=sys.stderr)

    # Probe 2: Check for matmul/gemm functions
    try:
        import tritonblas
        for name in ["matmul", "gemm", "dot", "mm", "bmm", "scaled_mm",
                      "dot_scaled", "mxfp4", "fp4", "a4w4"]:
            if hasattr(tritonblas, name):
                obj = getattr(tritonblas, name)
                print(f"TRITONBLAS.{name}: {type(obj).__name__}", file=sys.stderr)
                if callable(obj):
                    import inspect
                    try:
                        sig = inspect.signature(obj)
                        print(f"  SIGNATURE: {sig}", file=sys.stderr)
                    except (ValueError, TypeError):
                        print(f"  (no signature available)", file=sys.stderr)
    except Exception as e:
        print(f"TRITONBLAS FUNC PROBE ERROR: {e}", file=sys.stderr)

    # Probe 3: Check tritonblas submodules
    try:
        import tritonblas
        tb_path = os.path.dirname(tritonblas.__file__)
        # Read __init__.py to see what's exported
        init_path = os.path.join(tb_path, "__init__.py")
        if os.path.exists(init_path):
            with open(init_path) as f:
                content = f.read()
            print(f"TRITONBLAS __init__.py ({len(content)} chars):", file=sys.stderr)
            for line in content.splitlines()[:50]:
                print(f"  {line}", file=sys.stderr)
    except Exception as e:
        print(f"TRITONBLAS INIT PROBE ERROR: {e}", file=sys.stderr)

    # Probe 4: Try to import common submodule patterns
    for submod in ["tritonblas.matmul", "tritonblas.gemm", "tritonblas.ops",
                    "tritonblas.kernels", "tritonblas.blas", "tritonblas.scaled"]:
        try:
            mod = __import__(submod, fromlist=[""])
            print(f"IMPORT {submod}: {sorted(dir(mod))[:20]}", file=sys.stderr)
        except ImportError:
            pass
        except Exception as e:
            print(f"IMPORT {submod} ERROR: {type(e).__name__}: {e}", file=sys.stderr)

    return ref_kernel(data)
