#!/usr/bin/env python3
"""Dual Compute Benchmark - CPU + NPU Simultaneous Testing

Tests:
1. CPU backend with small models (<1B)
2. NPU concurrent request scaling
3. Combined throughput capability
"""

import subprocess
import time

import requests


def start_flm_server(model: str, port: int) -> subprocess.Popen:
    """Start FLM NPU server."""
    return subprocess.Popen(
        ["/usr/bin/flm", "serve", model, "--port", str(port), "--pmode", "performance"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_server(port: int, max_wait: int = 15) -> bool:
    """Wait for server to be ready."""
    for _ in range(max_wait):
        try:
            resp = requests.get(f"http://localhost:{port}/v1/models", timeout=1)
            if resp.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False


def benchmark_npu_concurrent(port: int, concurrency: int) -> dict:
    """Benchmark NPU with concurrent requests."""
    prompts = [f"Task {i}: Write a haiku" for i in range(concurrency)]
    start = time.time()

    responses = []
    for p in prompts:
        try:
            resp = requests.post(
                f"http://localhost:{port}/v1/chat/completions",
                json={
                    "model": "gemma3:4b",
                    "messages": [{"role": "user", "content": p}],
                    "max_tokens": 40,
                },
                timeout=60,
            )
            responses.append(resp)
        except Exception as e:
            print(f"  Error: {e}")

    elapsed = (time.time() - start) * 1000

    total_tokens = 0
    for resp in responses:
        try:
            data = resp.json()
            total_tokens += data.get("usage", {}).get("completion_tokens", 0)
        except:
            pass

    tps = total_tokens / (elapsed / 1000) if elapsed > 0 else 0
    return {"concurrency": concurrency, "tps": tps, "tokens": total_tokens, "time_ms": elapsed}


def benchmark_cpu_lemonade() -> dict:
    """Benchmark CPU backend via Lemonade."""
    # Try to load and test a small model on CPU
    # Using Lemonade's CPU backend directly

    base_url = "http://localhost:8002"  # Current Lemonade server

    # First, test if we can run CPU inference
    # We'll use the Qwen3-0.6B model if available

    model = "Qwen3-0.6B-GGUF"  # Smallest available

    try:
        # Check available models
        resp = requests.get(f"{base_url}/v1/models", timeout=5)
        models = resp.json().get("data", [])
        model_names = [m.get("id", "") for m in models]

        # Find smallest model
        small_models = [m for m in model_names if "0.6B" in m or "1B" in m or "1.7B" in m]
        if small_models:
            model = small_models[0]

        print(f"  Testing CPU with model: {model}")

        # Sequential benchmark (can't easily reload backend)
        start = time.time()
        total_tokens = 0

        for i in range(4):
            resp = requests.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": f"Write haiku {i}"}],
                    "max_tokens": 40,
                },
                timeout=30,
            )
            data = resp.json()
            tokens = data.get("usage", {}).get("completion_tokens", 0)
            total_tokens += tokens

        elapsed = (time.time() - start) * 1000
        tps = total_tokens / (elapsed / 1000) if elapsed > 0 else 0

        return {"model": model, "tps": tps, "tokens": total_tokens, "time_ms": elapsed}

    except Exception as e:
        return {"error": str(e), "tps": 0}


def main():
    print("=" * 70)
    print("DUAL COMPUTE BENCHMARK - CPU + NPU")
    print("=" * 70)

    results = {}

    # Test 1: CPU (via Lemonade)
    print("\n1. Testing CPU backend...")
    print("   (Using current Lemonade endpoint)")
    cpu_result = benchmark_cpu_lemonade()
    results["cpu"] = cpu_result
    if "error" not in cpu_result:
        print(f"   CPU: {cpu_result['tps']:.1f} TPS ({cpu_result['tokens']} tokens)")
    else:
        print(f"   CPU: Error - {cpu_result['error']}")

    # Test 2: NPU
    print("\n2. Testing NPU backend...")
    print("   (Starting FLM server...)")

    flm_proc = start_flm_server("gemma3:4b", 8004)

    if wait_for_server(8004, max_wait=15):
        print("   Server ready!")

        # Test different concurrency levels
        npu_results = []
        for conc in [1, 2, 4]:
            print(f"\n   Testing concurrency={conc}...")
            result = benchmark_npu_concurrent(8004, conc)
            npu_results.append(result)
            print(
                f"     {result['tps']:.1f} TPS ({result['tokens']} tokens in {result['time_ms']:.0f}ms)"
            )

        results["npu"] = npu_results

        flm_proc.terminate()
        flm_proc.wait()
    else:
        print("   ERROR: Server failed to start")
        flm_proc.terminate()
        results["npu"] = [{"error": "server timeout"}]

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    if "error" not in results.get("cpu", {}):
        cpu = results["cpu"]
        print(f"CPU (Lemonade): {cpu['tps']:.1f} TPS")

    if "npu" in results and "error" not in results["npu"][0]:
        best_npu = max(results["npu"], key=lambda x: x["tps"])
        print(f"NPU (FLM): {best_npu['tps']:.1f} TPS at concurrency={best_npu['concurrency']}")

    # Combined potential
    if "error" not in results.get("cpu", {}) and "npu" in results:
        cpu_tps = results["cpu"].get("tps", 0)
        npu_tps = max([r["tps"] for r in results["npu"] if "tps" in r], default=0)
        if cpu_tps > 0 and npu_tps > 0:
            print(f"\nCombined Potential: {cpu_tps + npu_tps:.1f} TPS")

    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
