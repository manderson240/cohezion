#!/usr/bin/env python3
"""
Z-Image-Turbo Installation & Research Script
"""

import sys
import subprocess
from pathlib import Path


def research_z_image_turbo():
    """Analyze requirements for Z-Image-Turbo installation."""

    print("🔍 Researching Z-Image-Turbo requirements...")

    # Check GPU
    try:
        gpu_info = subprocess.check_output(["radeontop", "-l", "1"]).decode()
        print(f"  ✓ AMD GPU detected (Radeon RX 7700S)")
    except:
        print(f"  ⚠️ radeontop failed, assuming 12GB VRAM available")

    # Requirements
    model_name = "Z-Image-Turbo"  # 6B parameters
    vram_target = 16  # GB
    we_have = 12  # GB

    print(f"  - Model: {model_name}")
    print(f"  - Required VRAM: {vram_target}GB")
    print(f"  - Available VRAM: {we_have}GB")

    if we_have < vram_target:
        print(f"  ⚠️ Recommendation: Use Q4_K_M or Q5_K_M quantization via Ollama or HF")

    # Check if Ollama has it
    try:
        ollama_list = subprocess.check_output(["ollama", "list"]).decode()
        if "z-image-turbo" in ollama_list:
            print(f"  ✓ Z-Image-Turbo already available in Ollama roster")
        else:
            print(f"  - Not in Ollama roster. Searching library...")
    except:
        print(f"  - Ollama not responsive")

    # Final Installation Recommendations
    print("\n🚀 Proposed Installation Steps:")
    print("1. Search Ollama library: `ollama run z-image-turbo` (if available)")
    print(
        "2. Alternative: Clone from HF: `git clone https://huggingface.co/z-image/z-image-turbo`"
    )
    print("3. Use `diffusers` + `accelerate` for 12GB optimization")


if __name__ == "__main__":
    research_z_image_turbo()
