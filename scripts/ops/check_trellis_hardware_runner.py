#!/usr/bin/env python3
"""Check real TRELLIS PyTorch / ROCm runtime pipeline and Lemonade TRELLIS-3D backend status."""

from __future__ import annotations

import subprocess

import torch


print("=" * 80)
print("  🔍 AUDITING LOCAL HARDWARE & PYTORCH ENVIRONMENT FOR REAL TRELLIS-3D RUNNER")
print("=" * 80)

print(f"PyTorch Version: {torch.__version__}")
print(f"ROCm / HIP Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Device Count: {torch.cuda.device_count()}")
    print(f"Device Name: {torch.cuda.get_device_name(0)}")

# Check if native Microsoft TRELLIS repo / packages are installed
for pkg in ["trellis", "spconv", "nvdiffrast", "diff_gaussian_rasterization", "cumesh"]:
    try:
        __import__(pkg)
        print(f"  ✓ Native PyTorch Package '{pkg}': INSTALLED")
    except ImportError:
        print(f"  ✗ Native PyTorch Package '{pkg}': NOT INSTALLED (Missing in Python virtualenv)")

# Check Lemonade TRELLIS server binary
try:
    res = subprocess.run(["which", "trellis-server"], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  ✓ Found 'trellis-server' binary at: {res.stdout.strip()}")
    else:
        print("  ✗ 'trellis-server' standalone binary not in PATH")
except Exception as e:
    print(f"  ✗ Error checking trellis-server: {e}")

print("=" * 80)
