"""Kaggle Environment Auditor — Deep system discovery for agentic course-correction."""

import os
import platform
import subprocess
import sys
from pathlib import Path

import psutil
import torch


def audit():
    print("=== 🛠️ KAG-AUDIT: DEEP ENVIRONMENT DISCOVERY ===")

    # 1. OS & Runtime
    print(f"[OS] Platform: {platform.platform()}")
    print(f"[OS] Python: {sys.version}")
    print(f"[OS] User: {os.getlogin() if hasattr(os, 'getlogin') else 'unknown'}")

    # 2. Compute (CPU/RAM)
    mem = psutil.virtual_memory()
    print(
        f"[CPU] Cores: {psutil.cpu_count(logical=False)} (physical), {psutil.cpu_count(logical=True)} (logical)"
    )
    print(
        f"[MEM] Total: {mem.total / (1024**3):.2f} GB | Available: {mem.available / (1024**3):.2f} GB"
    )

    # 3. GPU/CUDA Details
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            prop = torch.cuda.get_device_properties(i)
            print(f"[GPU {i}] Name: {prop.name}")
            print(f"[GPU {i}] VRAM: {prop.total_memory / (1024**3):.2f} GB")
            print(f"[GPU {i}] Capability: {prop.major}.{prop.minor}")

        print(f"[CUDA] Version: {torch.version.cuda}")
        print(f"[CUDA] Arch List: {torch.cuda.get_arch_list()}")

        # Check for Blackwell specific binaries if environment is G4
        ptxas_path = os.environ.get("TRITON_PTXAS_PATH", "/usr/local/cuda/bin/ptxas")
        if os.path.exists(ptxas_path):
            print(f"[CUDA] ptxas found at: {ptxas_path}")
            res = subprocess.run([ptxas_path, "--version"], capture_output=True, text=True)
            print(
                f"[CUDA] ptxas version: {res.stdout.splitlines()[0] if res.stdout else 'unknown'}"
            )
    else:
        print("[GPU] CUDA NOT AVAILABLE")

    # 4. Library Versions (The "Wall of Red" preventers)
    libs = [
        "transformers",
        "vllm",
        "trl",
        "bitsandbytes",
        "peft",
        "polars",
        "sympy",
        "numpy",
        "pandas",
    ]
    print("[LIBS] Version Check:")
    for lib in libs:
        try:
            mod = __import__(lib)
            version = getattr(mod, "__version__", "unknown")
            print(f"  - {lib}: {version}")
        except ImportError:
            print(f"  - {lib}: NOT INSTALLED")

    # 5. I/O & Mount Points
    print("[I/O] Mount Points:")
    mounts = ["/kaggle/input", "/kaggle/working", "/kaggle/temp"]
    for m in mounts:
        path = Path(m)
        if path.exists():
            size = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file()) / (1024**2)
            print(f"  - {m}: EXISTS ({size:.2f} MB used)")
        else:
            print(f"  - {m}: NOT FOUND")

    # 6. Network Capability
    try:
        import socket

        socket.create_connection(("8.8.8.8", 53), timeout=2)
        print("[NET] Internet: ENABLED")
    except:
        print("[NET] Internet: DISABLED")

    print("=== 🛠️ KAG-AUDIT COMPLETE ===\n")


if __name__ == "__main__":
    audit()
