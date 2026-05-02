#!/usr/bin/env python3
"""
Restart Lemonade Server with Full AMD Optimizations

Steps:
1. Set all AMD environment variables
2. Stop existing server
3. Start new server with optimizations
4. Verify health and performance
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests


# AMD Optimizations
AMD_ENV = {
    "RADV_PERFTEST": "aco,gpl,rt,nggc",
    "RADV_COOPERATIVE_MATRIX": "1",
    "MESA_SHADER_CACHE_DISABLE": "0",
    "MESA_SHADER_CACHE_MAX_SIZE": "4GB",
    "HSA_OVERRIDE_GFX_VERSION": "11.0.0",
    "HIP_VISIBLE_DEVICES": "0",
    "PATH": "/opt/rocm/bin:/usr/local/bin:/usr/bin:/bin",
}

MODEL = "DeepSeek-R1-0528-Qwen3-8B-Q4_1"
PORT = 8002


def stop_existing_server():
    """Stop existing Vulkan server."""
    print("=== Step 1: Stopping Existing Server ===")

    # Find and terminate existing process
    try:
        result = subprocess.run(
            ["pgrep", "-f", "llama-server.*vulkan.*8002"], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    print(f"  Stopping PID {pid}...")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            time.sleep(3)
            print("  ✓ Server stopped")
        else:
            print("  No existing server found")
    except Exception as e:
        print(f"  Warning: {e}")


def set_environment():
    """Set AMD environment variables."""
    print("\n=== Step 2: Setting AMD Environment ===")

    for key, value in AMD_ENV.items():
        os.environ[key] = value
        print(f"  {key}={value}")

    print("  ✓ Environment configured")


def start_optimized_server():
    """Start server with optimizations."""
    print("\n=== Step 3: Starting Optimized Server ===")

    cmd = [
        "lemonade",
        "serve",
        MODEL,
        "--backend",
        "vulkan",
        "--port",
        str(PORT),
        "--ctx-size",
        "4096",
        "--cache-type-k",
        "q8_0",
        "--cache-type-v",
        "q8_0",
        "--flash-attn",
        "--no-mmap",
        "--context-shift",
        "--keep",
        "16",
        "--reasoning-format",
        "auto",
        "--no-webui",
        "-ngl",
        "99",
    ]

    print(f"  Command: {' '.join(cmd)}")

    # Start server in background
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )

    print(f"  Started with PID {process.pid}")
    return process


def verify_server(timeout=60):
    """Wait for server and verify health."""
    print(f"\n=== Step 4: Verifying Server ({timeout}s timeout) ===")

    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"http://localhost:{PORT}/health", timeout=2)
            if r.status_code == 200:
                print(f"  ✓ Server healthy after {time.time() - start:.1f}s")
                return True
        except:
            pass
        time.sleep(1)
        print(f"  Waiting... ({int(time.time() - start)}s)")

    print("  ✗ Server failed to start")
    return False


def quick_benchmark():
    """Run quick benchmark to verify performance."""
    print("\n=== Step 5: Performance Verification ===")

    import concurrent.futures

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Write a Python function"}],
        "max_tokens": 64,
        "temperature": 0.5,
    }

    def make_request():
        start = time.time()
        r = requests.post(f"http://localhost:{PORT}/v1/chat/completions", json=payload, timeout=30)
        elapsed = time.time() - start
        tokens = r.json().get("usage", {}).get("completion_tokens", 0)
        return {"elapsed": elapsed, "tokens": tokens}

    # Test 4 concurrent
    print("  Running 4 concurrent requests...")
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(make_request) for _ in range(4)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_time = time.time() - start

    total_tokens = sum(r["tokens"] for r in results)
    tps = total_tokens / total_time

    print(f"  Total tokens: {total_tokens}")
    print(f"  Wall time: {total_time:.2f}s")
    print(f"  Throughput: {tps:.1f} TPS")

    if tps > 100:
        print("  ✅ EXCELLENT: Above 100 TPS threshold")
    elif tps > 90:
        print("  ✅ GOOD: Near optimized performance")
    else:
        print("  ⚠️  Below expected (target: 105+ TPS)")

    return tps


def set_power_profile():
    """Try to set GPU to high performance."""
    print("\n=== Step 6: Power Profile (optional) ===")

    # Note: Requires sudo
    power_file = Path("/sys/class/drm/card1/device/power_dpm_force_performance_level")
    if power_file.exists():
        try:
            current = power_file.read_text().strip()
            print(f"  Current profile: {current}")
            if current == "auto":
                print("  To set HIGH performance, run:")
                print(f"    sudo sh -c 'echo high > {power_file}'")
        except PermissionError:
            print("  ⚠️  Permission denied (requires sudo)")
            print(f"  Run manually: sudo sh -c 'echo high > {power_file}'")


def check_gpu_utilization():
    """Check GPU utilization."""
    print("\n=== Step 7: GPU Utilization ===")

    try:
        result = subprocess.run(["rocm-smi"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(result.stdout[:500])
    except:
        print("  rocm-smi not available")


def main():
    print("=" * 70)
    print("RESTART LEMONADE SERVER WITH AMD OPTIMIZATIONS")
    print("=" * 70)
    print()

    # Set environment first
    set_environment()

    # Stop existing
    stop_existing_server()

    # Start new
    server_proc = start_optimized_server()

    # Wait for startup
    if not verify_server(timeout=60):
        print("\n❌ Server failed to start")
        return 1

    # Benchmark
    try:
        tps = quick_benchmark()
    except Exception as e:
        print(f"\n⚠️ Benchmark failed: {e}")
        tps = 0

    # Optional checks
    set_power_profile()
    check_gpu_utilization()

    # Summary
    print("\n" + "=" * 70)
    print("RESTART COMPLETE")
    print("=" * 70)
    print(f"✓ Server running on port {PORT}")
    print("✓ AMD optimizations active")
    if tps > 0:
        print(f"✓ Performance: {tps:.1f} TPS")
    print()
    print("Test with:")
    print(f"  curl http://localhost:{PORT}/health")
    print("  python3 benchmark_amd_optimized.py")
    print()
    print("NOTE: Server is running as subprocess.")
    print("To daemonize, use: sudo systemctl start lemonade-optimized")

    return 0


if __name__ == "__main__":
    sys.exit(main())
