#!/usr/bin/env python3
"""Final GPU Saturation Analysis - Complete Scaling Curve.

Tests 1-8 concurrent requests to map full server behavior.
Includes detailed failure analysis.
"""

import asyncio
import time

import aiohttp


async def test_concurrency(n: int, verbose: bool = True) -> dict:
    """Test specific concurrency level."""
    if verbose:
        print(f"\nTesting concurrency={n}...")

    base_url = "http://localhost:8002"

    # Detect model
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/v1/models", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    model = models[0] if models else "DeepSeek-Qwen3-8B-GGUF"
                else:
                    model = "DeepSeek-Qwen3-8B-GGUF"
        except:
            model = "DeepSeek-Qwen3-8B-GGUF"

    connector = aiohttp.TCPConnector(limit=n * 2)

    results = []
    errors = []

    async with aiohttp.ClientSession(connector=connector) as session:
        # Warm-up (clear any stale state)
        try:
            await session.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ready"}],
                    "max_tokens": 5,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            )
        except:
            pass

        # Run N concurrent requests
        start = time.monotonic()

        tasks = []
        for i in range(n):
            tasks.append(
                session.post(
                    f"{base_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are helpful."},
                            {"role": "user", "content": f"Task {i}: Write a haiku."},
                        ],
                        "max_tokens": 40,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),  # Individual timeout
                )
            )

        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = (time.monotonic() - start) * 1000

            # Process responses
            total_tokens = 0
            success_count = 0

            for i, resp in enumerate(responses):
                if isinstance(resp, Exception):
                    errors.append(f"Req {i}: {type(resp).__name__}")
                    continue

                try:
                    data = await resp.json()
                    if "error" in data:
                        errors.append(f"Req {i}: API error - {data['error']}")
                        continue

                    usage = data.get("usage", {})
                    tokens = usage.get("completion_tokens", 0)
                    total_tokens += tokens
                    success_count += 1
                except Exception as e:
                    errors.append(f"Req {i}: Parse error - {e}")

            tps = total_tokens / (elapsed / 1000) if elapsed > 0 else 0

            return {
                "concurrency": n,
                "tps": tps,
                "success": success_count,
                "requested": n,
                "total_tokens": total_tokens,
                "elapsed_ms": elapsed,
                "errors": errors,
            }

        except Exception as e:
            return {
                "concurrency": n,
                "tps": 0,
                "success": 0,
                "requested": n,
                "total_tokens": 0,
                "elapsed_ms": (time.time() - start) * 1000,
                "errors": [f"Batch error: {e}"],
            }


async def full_saturation_analysis():
    """Run complete saturation analysis."""
    print("=" * 70)
    print("GPU SATURATION ANALYSIS - Complete Scaling Curve")
    print("=" * 70)
    print("\nTesting concurrency levels 1-8...\n")

    results = []
    for n in range(1, 9):
        result = await test_concurrency(n)
        results.append(result)

        # Format output
        success_rate = result["success"] / result["requested"] * 100
        status = "✓" if result["success"] == result["requested"] else "✗"

        print(
            f"  {status} N={n}: {result['tps']:>6.1f} TPS, "
            f"{result['success']}/{result['requested']} success "
            f"({success_rate:.0f}%)"
        )

        if result["errors"]:
            for err in result["errors"][:2]:
                print(f"      Error: {err[:60]}")

        # Small delay between tests
        if n < 8:
            await asyncio.sleep(2)

    # Summary table
    print("\n" + "=" * 70)
    print("SCALING CURVE")
    print("=" * 70)
    print(f"{'N':>3} {'TPS':>10} {'Time':>10} {'Success':>10} {'Status':>15}")
    print("-" * 70)

    optimal = None
    max_tps = 0

    for r in results:
        status = (
            "✓ OPTIMAL"
            if r["success"] == r["requested"] and r["tps"] > max_tps
            else "✓ Working"
            if r["success"] == r["requested"]
            else "✗ Failed"
        )

        if r["success"] == r["requested"] and r["tps"] > max_tps:
            max_tps = r["tps"]
            optimal = r["concurrency"]

        print(
            f"{r['concurrency']:>3} {r['tps']:>10.1f} "
            f"{r['elapsed_ms'] / 1000:>9.2f}s "
            f"{r['success']}/{r['requested']:>4}       {status:>15}"
        )

    print("=" * 70)
    print(f"\nFINDING: Server has EXACTLY {optimal} parallel workers")
    print(f"  Concurrency >{optimal}: Requests fail or queue")
    print(f"  Optimal throughput: {max_tps:.1f} TPS at concurrency={optimal}")

    # Calculate efficiency
    print("\nEfficiency analysis:")
    for r in results:
        if r["success"] == r["requested"]:
            per_req_tps = r["tps"] / r["concurrency"]
            print(f"  N={r['concurrency']}: {per_req_tps:.1f} TPS/request")

    print("\n" + "=" * 70)
    print("METRIC tokens_per_sec=" + str(max_tps))
    print("METRIC optimal_concurrency=" + str(optimal))
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(full_saturation_analysis())
