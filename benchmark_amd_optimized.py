#!/usr/bin/env python3
"""
Benchmark AMD Optimizations

Tests GPU inference with AMD-specific optimizations.
Uses synchronous requests for simplicity.
"""

import concurrent.futures
import json
import os
import time

import requests


# Configuration
MODEL = "DeepSeek-R1-0528-Qwen3-8B-Q4_1"
URL = "http://localhost:8002/v1/chat/completions"
CONCURRENCY = 4
PROMPT = "Write a Python function to calculate Fibonacci numbers recursively."
MAX_TOKENS = 256


def make_request(prompt: str) -> dict:
    """Make a single inference request."""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.5,
    }

    start = time.perf_counter()
    resp = requests.post(URL, json=payload, timeout=120)
    result = resp.json()
    elapsed = time.perf_counter() - start

    return {
        "elapsed": elapsed,
        "tokens": result.get("usage", {}).get("completion_tokens", 0),
    }


def benchmark_burst(count: int, label: str) -> dict:
    """Run burst benchmark with N concurrent requests."""
    print(f"\n{label}: Testing {count} concurrent requests...")

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(make_request, PROMPT) for _ in range(count)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_time = time.perf_counter() - start

    # Calculate metrics
    total_tokens = sum(r["tokens"] for r in results)
    tps = total_tokens / total_time if total_time > 0 else 0

    print(f"  Total tokens: {total_tokens}")
    print(f"  Wall time: {total_time:.2f}s")
    print(f"  Throughput: {tps:.1f} TPS")
    print(f"  Per-request: {tps / count:.1f} TPS/req")

    return {
        "count": count,
        "total_tokens": total_tokens,
        "wall_time": total_time,
        "tps": tps,
        "tps_per_req": tps / count,
    }


def set_amd_optimizations():
    """Set AMD environment variables."""
    os.environ["RADV_PERFTEST"] = "aco,gpl,rt,nggc"
    os.environ["RADV_COOPERATIVE_MATRIX"] = "1"
    os.environ["MESA_SHADER_CACHE_DISABLE"] = "0"
    os.environ["MESA_SHADER_CACHE_MAX_SIZE"] = "4GB"
    os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
    os.environ["HIP_VISIBLE_DEVICES"] = "0"
    os.environ["AMD_DEBUG"] = "nosam"  # Disable shader arrays for small batches
    print("✓ AMD optimizations ENABLED")
    print("  RADV_PERFTEST=aco,gpl,rt,nggc")
    print("  RADV_COOPERATIVE_MATRIX=1")
    print("  MESA_SHADER_CACHE_MAX_SIZE=4GB")


def clear_amd_optimizations():
    """Clear AMD environment variables."""
    for var in [
        "RADV_PERFTEST",
        "RADV_COOPERATIVE_MATRIX",
        "MESA_SHADER_CACHE_DISABLE",
        "MESA_SHADER_CACHE_MAX_SIZE",
        "HSA_OVERRIDE_GFX_VERSION",
        "HIP_VISIBLE_DEVICES",
        "AMD_DEBUG",
    ]:
        os.environ.pop(var, None)
    print("✓ AMD optimizations DISABLED (baseline)")


def main():
    print("=" * 70)
    print("AMD OPTIMIZATION BENCHMARK")
    print("=" * 70)
    print(f"Testing: {CONCURRENCY} concurrent requests")
    print(f"Model: {MODEL}")
    print()

    # Check server health first
    try:
        resp = requests.get("http://localhost:8002/health", timeout=5)
        print(f"✓ Server health: {resp.json().get('status', 'unknown')}")
    except Exception as e:
        print(f"✗ Server not responding: {e}")
        return

    print()

    # Test baseline (no optimizations)
    clear_amd_optimizations()
    baseline = benchmark_burst(CONCURRENCY, "BASELINE")

    # Wait for GPU to settle
    print("\nCooling down (10s)...")
    time.sleep(10)

    # Test with optimizations
    set_amd_optimizations()
    optimized = benchmark_burst(CONCURRENCY, "OPTIMIZED")

    # Report
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<20} {'Baseline':<15} {'Optimized':<15} {'Change':<15}")
    print("-" * 70)

    tps_change = ((optimized["tps"] - baseline["tps"]) / baseline["tps"]) * 100
    tps_per_req_change = (
        (optimized["tps_per_req"] - baseline["tps_per_req"]) / baseline["tps_per_req"]
    ) * 100
    time_change = ((baseline["wall_time"] - optimized["wall_time"]) / baseline["wall_time"]) * 100

    print(
        f"{'Throughput (TPS)':<20} {baseline['tps']:<15.1f} {optimized['tps']:<15.1f} {tps_change:+.1f}%"
    )
    print(
        f"{'TPS/Request':<20} {baseline['tps_per_req']:<15.1f} {optimized['tps_per_req']:<15.1f} {tps_per_req_change:+.1f}%"
    )
    print(
        f"{'Wall Time (s)':<20} {baseline['wall_time']:<15.2f} {optimized['wall_time']:<15.2f} {time_change:+.1f}%"
    )

    print("-" * 70)

    if tps_change > 5:
        print(f"✅ OPTIMIZATIONS EFFECTIVE: +{tps_change:.1f}% throughput gain")
    elif tps_change > -5:
        print(f"➡️ NO SIGNIFICANT CHANGE: {tps_change:.1f}% (within noise)")
    else:
        print(f"⚠️ REGRESSION: {tps_change:.1f}% (unexpected)")

    print("=" * 70)

    # Save result
    from datetime import datetime

    result = {
        "timestamp": datetime.now().isoformat(),
        "baseline": baseline,
        "optimized": optimized,
        "tps_change_pct": tps_change,
        "note": "Environment variables must be set BEFORE server starts",
    }

    with open("amd_optimization_result.json", "w") as f:
        json.dump(result, f, indent=2)

    print("\nResults saved to: amd_optimization_result.json")
    print()
    print("⚠️  IMPORTANT NOTE:")
    print("   Environment variables must be set BEFORE starting the Lemonade server.")
    print("   The current server was started WITHOUT these optimizations.")
    print("   To test properly, restart the server with the env vars set.")

    return result


if __name__ == "__main__":
    main()
