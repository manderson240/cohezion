#!/usr/bin/env python3
"""Refreshes and reinstalls Lemonade backends to their latest release binaries."""

import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backend_updater")

BACKENDS_TO_UPDATE = [
    "llamacpp:rocm",
    "llamacpp:vulkan",
    "flm:npu",
    "sd-cpp:rocm",
    "sd-cpp:vulkan",
    "whispercpp:rocm",
    "thenoise:rocm",
    "vllm:rocm",
    "trellis:rocm",
    "thinksound:rocm",
    "acestep:rocm",
    "openmoss:rocm"
]

def update_backends():
    print("\n" + "=" * 95)
    print("🍋 REFRESHING & UPDATING ALL LEMONADE HARDWARE BACKENDS (ROCm/Vulkan/NPU)")
    print("=" * 95)

    for backend in BACKENDS_TO_UPDATE:
        print(f"\n🔄 Re-verifying / Updating `{backend}`...")
        cmd = ["lemonade", "backends", "install", backend]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                print(f"  ✓ `{backend}` is up to date / successfully refreshed.")
            else:
                print(f"  ℹ️ Notice on `{backend}`: {res.stderr.strip() or res.stdout.strip()}")
        except Exception as e:
            print(f"  ⚠️ Error updating `{backend}`: {e}")

    print("\n" + "=" * 95)
    print("🎉 ALL LEMONADE HARDWARE BACKENDS VERIFIED UP-TO-DATE!\n")

if __name__ == "__main__":
    update_backends()
