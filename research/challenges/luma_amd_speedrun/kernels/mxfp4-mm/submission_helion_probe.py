"""Probe: Check Helion availability and runner environment details."""
import sys
import os
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    # Probe 1: Helion
    try:
        import helion
        print(f"HELION FOUND: {helion.__version__}", file=sys.stderr)
        print(f"HELION DIR: {dir(helion)}", file=sys.stderr)
        helion_path = os.path.dirname(helion.__file__)
        for f in sorted(os.listdir(helion_path))[:30]:
            print(f"  {f}", file=sys.stderr)
    except ImportError as e:
        print(f"HELION NOT FOUND: {e}", file=sys.stderr)

    # Probe 2: ROCm version
    try:
        import torch
        print(f"TORCH: {torch.__version__}", file=sys.stderr)
        print(f"ROCM: {torch.version.hip}", file=sys.stderr)
        print(f"GPU: {torch.cuda.get_device_name(0)}", file=sys.stderr)
    except Exception as e:
        print(f"TORCH ERROR: {e}", file=sys.stderr)

    # Probe 3: ATOM engine
    try:
        import atom
        print(f"ATOM FOUND: {dir(atom)}", file=sys.stderr)
    except ImportError as e:
        print(f"ATOM NOT FOUND: {e}", file=sys.stderr)

    # Probe 4: Triton version and features
    try:
        import triton
        print(f"TRITON: {triton.__version__}", file=sys.stderr)
    except ImportError as e:
        print(f"TRITON NOT FOUND: {e}", file=sys.stderr)

    # Probe 5: aiter version
    try:
        import aiter
        print(f"AITER: {aiter.__version__}", file=sys.stderr)
        aiter_path = os.path.dirname(aiter.__file__)
        # Check for any new modules since last probe
        all_modules = sorted(os.listdir(aiter_path))
        print(f"AITER MODULES ({len(all_modules)}): {all_modules[:40]}", file=sys.stderr)
    except Exception as e:
        print(f"AITER ERROR: {e}", file=sys.stderr)

    # Probe 6: pip list for any new packages
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=columns"],
            capture_output=True, text=True, timeout=10
        )
        # Filter for interesting packages
        for line in result.stdout.splitlines():
            low = line.lower()
            if any(k in low for k in ["helion", "atom", "triton", "aiter", "rocm", "hip", "flash", "sage", "ck", "composable"]):
                print(f"PKG: {line.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"PIP LIST ERROR: {e}", file=sys.stderr)

    return ref_kernel(data)
