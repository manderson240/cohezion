#!/usr/bin/env python3
"""
Lemonade Optimized Launcher

Launches Lemonade with AMD-specific optimizations:
- ROCm gfx1151 override (HSA_OVERRIDE_GFX_VERSION=11.0.0)
- Vulkan RADV optimizations
- KV cache quantization
- Flash attention
- Power profile

Usage:
    python3 lemonade_amd_optimized_launcher.py [gpu|npu|cpu] [model]
"""

import os
import subprocess
import sys
from pathlib import Path


# AMD Optimizations
AMD_ENV = {
    # ROCm/HIP
    "HSA_OVERRIDE_GFX_VERSION": "11.0.0",  # Unlock gfx1151
    "HIP_VISIBLE_DEVICES": "0",
    "PATH": "/opt/rocm/bin:" + os.environ.get("PATH", ""),

    # Vulkan RADV
    "RADV_PERFTEST": "aco,gpl,rt,nggc",
    "RADV_COOPERATIVE_MATRIX": "1",
    "MESA_SHADER_CACHE_DISABLE": "0",
    "MESA_SHADER_CACHE_MAX_SIZE": "4GB",

    # llama.cpp
    "GGML_VULKAN_LAYER_NB": "1",  # Single queue for lower latency
}

def set_power_profile_high():
    """Set GPU to high performance profile."""
    power_file = Path("/sys/class/drm/card1/device/power_dpm_force_performance_level")
    if power_file.exists():
        try:
            # Needs sudo
            subprocess.run(
                ["sudo", "tee", str(power_file)],
                input="high\n",
                text=True,
                check=True,
                capture_output=True
            )
            print("✓ Power profile set to HIGH")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Could not set power profile (needs sudo): {e}")
            return False
    return False

def launch_gpu_optimized(model_id: str = "DeepSeek-R1-0528-Qwen3-8B-Q4_1"):
    """Launch GPU server with AMD optimizations."""

    # Environment setup
    env = os.environ.copy()
    env.update(AMD_ENV)

    print("=" * 70)
    print("🚀 LAUNCHING LEMONADE GPU WITH AMD OPTIMIZATIONS")
    print("=" * 70)
    print()

    # Set power profile
    set_power_profile_high()

    # Build optimized command
    cmd = [
        "lemonade", "serve",
        model_id,
        "--backend", "vulkan",
        "--port", "8002",
        "--ctx-size", "4096",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--flash-attn",
        "--no-mmap",
        "--context-shift",
        "--keep", "16",
        "--reasoning-format", "auto",
        "--no-webui",
        "-ngl", "99",
    ]

    print("Command:", " ".join(cmd))
    print()
    print("Environment:")
    for k, v in AMD_ENV.items():
        print(f"  {k}={v}")
    print()
    print("Optimizations:")
    print("  ✓ HSA_OVERRIDE_GFX_VERSION=11.0.0 (Unlock gfx1151)")
    print("  ✓ KV cache quantized to Q8_0 (50% memory savings)")
    print("  ✓ Flash Attention enabled (2x speed for long context)")
    print("  ✓ No memory-mapped I/O (faster on UMA)")
    print("  ✓ RADV cooperative matrix (AI acceleration)")
    print()

    # Launch
    subprocess.run(cmd, env=env)

def launch_npu(model_id: str = "gemma4:e2b"):
    """Launch NPU server (FLM)."""

    print("=" * 70)
    print("🚀 LAUNCHING LEMONADE NPU (FLM)")
    print("=" * 70)
    print()

    # FLM uses its own binary
    cmd = [
        "/usr/bin/flm", "serve",
        model_id,
        "--port", "8004",
    ]

    print("Command:", " ".join(cmd))
    print()
    print("Note: FLM is proprietary and doesn't support llama.cpp args")
    print()

    subprocess.run(cmd)

def launch_cpu_optimized(model_id: str = "Qwen3-0.6B-Q4_0"):
    """Launch CPU server with optimizations."""

    env = os.environ.copy()

    print("=" * 70)
    print("🚀 LAUNCHING LEMONADE CPU (Zen 5)")
    print("=" * 70)
    print()

    binary_path = "/var/lib/lemonade/.cache/lemonade/bin/llamacpp/cpu/llama-server"

    if not Path(binary_path).exists():
        print(f"Binary not found: {binary_path}")
        print("Using lemonade serve instead...")
        cmd = [
            "lemonade", "serve",
            model_id,
            "--backend", "cpu",
            "--port", "8006",
            "--ctx-size", "4096",
        ]
    else:
        # Direct binary launch
        cmd = [
            binary_path,
            "-m", "/var/lib/lemonade/.cache/huggingface/hub/models--unsloth--Qwen3-0.6B-GGUF/snapshots/*/Qwen3-0.6B-Q4_0.gguf",
            "--port", "8006",
            "--ctx-size", "4096",
            "-t", "16",  # 16 threads
        ]

    print("Command:", " ".join(cmd))
    print()

    subprocess.run(cmd, env=env)

def benchmark_suite():
    """Run benchmark with all optimizations."""

    env = os.environ.copy()
    env.update(AMD_ENV)

    print("=" * 70)
    print("🏁 RUNNING AMD OPTIMIZED BENCHMARK SUITE")
    print("=" * 70)
    print()

    # Quick TPS test
    print("Testing GPU endpoint...")
    import json
    import urllib.request

    payload = json.dumps({
        "model": "DeepSeek-R1-0528-Qwen3-8B-Q4_1",
        "messages": [{"role": "user", "content": "Write a Python function to calculate Fibonacci numbers"}],
        "max_tokens": 256,
        "temperature": 0.5,
    }).encode()

    req = urllib.request.Request(
        "http://localhost:8002/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        start = __import__('time').time()
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        elapsed = __import__('time').time() - start

        tokens = result.get('usage', {}).get('completion_tokens', 0)
        tps = tokens / elapsed if elapsed > 0 else 0

        print(f"✓ Benchmark complete: {tps:.1f} TPS")
        print(f"  Tokens: {tokens}, Time: {elapsed:.2f}s")
        print("  Quality: Reasoning content present" if result.get('choices', [{}])[0].get('message', {}).get('reasoning_content') else "  Quality: Standard output")
    except Exception as e:
        print(f"✗ Benchmark failed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: lemonade_amd_optimized_launcher.py [gpu|npu|cpu|benchmark] [model]")
        sys.exit(1)

    mode = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else None

    if mode == "gpu":
        launch_gpu_optimized(model or "DeepSeek-R1-0528-Qwen3-8B-Q4_1")
    elif mode == "npu":
        launch_npu(model or "gemma4:e2b")
    elif mode == "cpu":
        launch_cpu_optimized(model or "Qwen3-0.6B-Q4_0")
    elif mode == "benchmark":
        benchmark_suite()
    else:
        print(f"Unknown mode: {mode}")
        print("Use: gpu, npu, cpu, or benchmark")

if __name__ == "__main__":
    main()
