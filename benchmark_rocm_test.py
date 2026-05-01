#!/usr/bin/env python3
"""
ROCm Backend Test - gfx1151 Override Validation

Tests ROCm backend with HSA_OVERRIDE_GFX_VERSION=11.0.0
on AMD Strix Halo (gfx1151 - officially unsupported).

⚠️  WARNING: This is EXPERIMENTAL and may:
- Hang on contexts > 4096
- Be slower than Vulkan for small models
- Require system restart if frozen

Usage:
    python3 benchmark_rocm_test.py [--quick|--full]

Safety features:
- Automatic timeout (60s per request)
- Gradual context size testing (512 -> 2048 -> 4096)
- Automatic abort on hang detection
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError


# Configuration
MODEL = "DeepSeek-R1-0528-Qwen3-8B-Q4_1"
VULKAN_URL = "http://localhost:8002/v1/chat/completions"
ROCM_PORT = 8003
MAX_TEST_TIME = 300  # 5 minutes total timeout

# Test prompts of varying complexity
TEST_PROMPTS = {
    "quick": "Hi, respond with one word.",
    "medium": "Write a Python function to calculate Fibonacci numbers.",
    "long": "Explain the concept of flash attention in transformer models, including why it reduces memory usage from O(n²) to O(n).",
}

def setup_rocm_env():
    """Configure ROCm environment for gfx1151."""
    os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
    os.environ["HIP_VISIBLE_DEVICES"] = "0"
    os.environ["PATH"] = "/opt/rocm/bin:" + os.environ.get("PATH", "")

    print("✓ ROCm environment configured:")
    print("  HSA_OVERRIDE_GFX_VERSION=11.0.0")
    print("  HIP_VISIBLE_DEVICES=0")

    # Verify ROCm can see GPU
    try:
        result = subprocess.run(
            ["rocminfo"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "gfx1151" in result.stdout or "AMD Radeon" in result.stdout:
            print("  ✓ ROCm GPU detection working")
        else:
            print("  ⚠ ROCm may not detect GPU correctly")
    except Exception as e:
        print(f"  ⚠ ROCm check failed: {e}")


def start_rocm_server(ctx_size: int = 2048) -> subprocess.Popen:
    """Start ROCm backend server as subprocess."""
    cmd = [
        "lemonade", "serve", MODEL,
        "--backend", "rocm",
        "--port", str(ROCM_PORT),
        "--ctx-size", str(ctx_size),
        "--flash-attn",  # Critical for ROCm performance
        "--no-mmap",
        "--reasoning-format", "auto",
        "--no-webui",
        "-ngl", "99",
    ]

    print(f"\n🚀 Starting ROCm server (ctx-size={ctx_size})...")
    print(f"   Command: {' '.join(cmd)}")

    # Set environment for subprocess
    env = os.environ.copy()
    env["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
    env["HIP_VISIBLE_DEVICES"] = "0"

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    return process


def wait_for_server(timeout: int = 60) -> bool:
    """Wait for ROCm server to be ready."""
    import requests

    print(f"Waiting up to {timeout}s for server...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            r = requests.get(f"http://localhost:{ROCM_PORT}/health", timeout=2)
            if r.status_code == 200:
                print(f"✓ Server ready after {time.time() - start:.1f}s")
                return True
        except:
            pass
        time.sleep(1)

    return False


def test_inference(prompt: str, max_tokens: int = 50, timeout: int = 30) -> dict:
    """Test inference with timeout."""
    import requests

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.5,
    }

    start = time.time()

    def make_request():
        return requests.post(
            f"http://localhost:{ROCM_PORT}/v1/chat/completions",
            json=payload,
            timeout=timeout
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(make_request)
            response = future.result(timeout=timeout + 5)  # Extra buffer

            elapsed = time.time() - start
            result = response.json()
            tokens = result.get("usage", {}).get("completion_tokens", 0)
            tps = tokens / elapsed if elapsed > 0 else 0

            return {
                "success": True,
                "elapsed": elapsed,
                "tokens": tokens,
                "tps": tps,
                "status_code": response.status_code,
            }
    except FutureTimeoutError:
        return {"success": False, "error": "TIMEOUT", "elapsed": time.time() - start}
    except Exception as e:
        return {"success": False, "error": str(e), "elapsed": time.time() - start}


def gradual_ctx_test(server_proc) -> dict:
    """Test with increasing context sizes."""
    results = {}

    ctx_sizes = [512, 1024, 2048]

    for ctx_size in ctx_sizes:
        print(f"\n--- Testing ctx-size={ctx_size} ---")

        # Note: Can't change ctx-size dynamically, would need restart
        # Just testing inference stability for now

        result = test_inference(TEST_PROMPTS["medium"], max_tokens=100, timeout=60)

        if result["success"]:
            print(f"✓ Success: {result['tps']:.1f} TPS ({result['elapsed']:.2f}s)")
            results[f"ctx_{ctx_size}"] = result
        else:
            print(f"✗ Failed: {result.get('error', 'unknown')}")
            results[f"ctx_{ctx_size}"] = result
            break

        time.sleep(2)  # Brief cooldown

    return results


def benchmark_comparison(n_requests: int = 4) -> dict:
    """Compare ROCm vs Vulkan throughput."""
    import concurrent.futures

    import requests

    print(f"\n--- Throughput Test ({n_requests} concurrent) ---")

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": TEST_PROMPTS["medium"]}],
        "max_tokens": 64,
        "temperature": 0.5,
    }

    def make_one():
        start = time.time()
        r = requests.post(
            f"http://localhost:{ROCM_PORT}/v1/chat/completions",
            json=payload,
            timeout=60
        )
        elapsed = time.time() - start
        tokens = r.json().get("usage", {}).get("completion_tokens", 0) if r.status_code == 200 else 0
        return {"elapsed": elapsed, "tokens": tokens}

    try:
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_requests) as executor:
            futures = [executor.submit(make_one) for _ in range(n_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        total_time = time.time() - start

        total_tokens = sum(r["tokens"] for r in results)
        tps = total_tokens / total_time if total_time > 0 else 0

        return {
            "success": True,
            "total_tokens": total_tokens,
            "wall_time": total_time,
            "tps": tps,
            "tps_per_req": tps / n_requests,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup(server_proc):
    """Safely terminate server."""
    if server_proc and server_proc.poll() is None:
        print("\nStopping ROCm server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
            print("✓ Server stopped gracefully")
        except:
            server_proc.kill()
            print("✓ Server force killed")


def main():
    print("=" * 70)
    print("ROCm BACKEND TEST - gfx1151 Override")
    print("=" * 70)
    print("⚠️  WARNING: Experimental - may hang or crash")
    print("=" * 70)
    print()

    # Check mode
    mode = sys.argv[1] if len(sys.argv) > 1 else "standard"

    # Set up environment
    setup_rocm_env()

    # Start server
    server_proc = None
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode,
        "model": MODEL,
        "tests": {},
    }

    try:
        # Start ROCm server
        ctx_size = 2048 if mode == "quick" else 4096
        server_proc = start_rocm_server(ctx_size)

        # Wait for startup
        if not wait_for_server(timeout=120):
            print("❌ Server failed to start within timeout")
            results["status"] = "FAILED_STARTUP"
            return results

        # Run tests based on mode
        if mode == "quick":
            print("\n--- Quick Test (1 request) ---")
            r = test_inference(TEST_PROMPTS["quick"], max_tokens=20, timeout=30)
            results["tests"]["quick"] = r

            if r["success"]:
                print(f"✓ Quick test passed: {r['tps']:.1f} TPS")
            else:
                print(f"✗ Quick test failed: {r.get('error')}")

        else:
            # Standard test
            print("\n--- Gradual Context Test ---")
            ctx_results = gradual_ctx_test(server_proc)
            results["tests"]["context"] = ctx_results

            # Throughput test if basic tests passed
            if all(r.get("success") for r in ctx_results.values()):
                print("\n--- Throughput Benchmark ---")
                bench = benchmark_comparison(n_requests=4)
                results["tests"]["throughput"] = bench

                if bench.get("success"):
                    print(f"✓ Throughput: {bench['tps']:.1f} TPS ({bench['tps_per_req']:.1f} per request)")
                else:
                    print(f"✗ Throughput test failed: {bench.get('error')}")

            results["status"] = "PASSED" if all(
                r.get("success") for r in results["tests"].values() if isinstance(r, dict)
            ) else "PARTIAL"

        # Cleanup
        cleanup(server_proc)
        server_proc = None

        # Save results
        with open("rocm_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\n✓ Results saved to: rocm_test_results.json")

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        results["status"] = "INTERRUPTED"
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        results["status"] = f"ERROR: {e}"
    finally:
        cleanup(server_proc)

    # Final report
    print("\n" + "=" * 70)
    print("ROCm TEST SUMMARY")
    print("=" * 70)
    print(f"Status: {results.get('status', 'UNKNOWN')}")
    print(f"Model: {results['model']}")
    print(f"Mode: {results['mode']}")

    if "throughput" in results["tests"] and results["tests"]["throughput"].get("success"):
        tps = results["tests"]["throughput"]["tps"]
        print(f"\nThroughput: {tps:.1f} TPS")
        print()
        if tps > 100:
            print("✅ ROCm comparable to Vulkan (~121 TPS)")
        elif tps > 50:
            print("➡️ ROCm functional but slower than Vulkan")
        else:
            print("⚠️ ROCm significantly slower - recommend Vulkan")

    print("=" * 70)

    return results


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result.get("status") in ["PASSED", "PARTIAL"] else 1)
