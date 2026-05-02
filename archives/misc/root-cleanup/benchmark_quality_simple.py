#!/usr/bin/env python3
"""Simple Quality Check - Does optimization preserve output coherence?"""

import asyncio
import time

import aiohttp


async def test_quality():
    """Test that optimized settings produce coherent outputs."""

    base_url = "http://localhost:8002"
    model = "DeepSeek-Qwen3-8B-GGUF"

    # Test with quality-optimized settings
    test_cases = [
        {
            "name": "Baseline (temp=0.7)",
            "system": "You are a helpful assistant.",
            "temperature": 0.7,
            "top_p": 0.9,
        },
        {
            "name": "Optimized (temp=0.3)",
            "system": "You are a precise reasoning assistant. Be factual and concise.",
            "temperature": 0.3,
            "top_p": 0.9,
        },
        {
            "name": "Throughput (temp=0.1, concurrent)",
            "system": "You are a helpful assistant.",
            "temperature": 0.1,
            "top_p": 0.9,
        },
    ]

    prompt = "Explain what makes a good software engineer in 2-3 sentences."

    async with aiohttp.ClientSession() as session:
        print("=" * 70)
        print("QUALITY COMPARISON: Different Optimization Strategies")
        print("=" * 70)

        results = []

        for case in test_cases:
            print(f"\n{'=' * 70}")
            print(f"Testing: {case['name']}")
            print(f"System: {case['system'][:60]}...")
            print(f"Temperature: {case['temperature']}")

            start = time.time()

            async with session.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": case["system"]},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": case["temperature"],
                    "top_p": case["top_p"],
                    "max_tokens": 100,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                elapsed = (time.time() - start) * 1000

                text = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("completion_tokens", 0)
                tps = tokens / (elapsed / 1000) if elapsed > 0 else 0

                print(f"\nOutput ({tokens} tokens, {elapsed:.0f}ms, {tps:.1f} TPS):")
                print(f'"{text[:200]}{"..." if len(text) > 200 else ""}"')

                # Simple quality: does it answer the question?
                has_substance = len(text.split()) > 10
                has_engineer = "engineer" in text.lower() or "engineering" in text.lower()
                has_quality = any(
                    w in text.lower()
                    for w in ["skill", "learn", "problem", "code", "communication"]
                )

                quality_pass = has_substance and has_engineer

                print("\nQuality Check:")
                print(
                    f"  Has substance (>10 words): {has_substance} ✓"
                    if has_substance
                    else "  Has substance: ✗"
                )
                print(
                    f"  Mentions engineering: {has_engineer} ✓"
                    if has_engineer
                    else "  Mentions engineering: ✗"
                )
                print(
                    f"  Has quality markers: {has_quality} ✓"
                    if has_quality
                    else "  Has quality markers: ✗"
                )
                print(f"  OVERALL: {'PASS ✓' if quality_pass else 'FAIL ✗'}")

                results.append(
                    {
                        "name": case["name"],
                        "tps": tps,
                        "quality_pass": quality_pass,
                        "tokens": tokens,
                    }
                )

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"{'Strategy':<35} {'TPS':<10} {'Quality':<10}")
        print("-" * 70)

        for r in results:
            status = "PASS ✓" if r["quality_pass"] else "FAIL ✗"
            print(f"{r['name']:<35} {r['tps']:<10.1f} {status:<10}")

        # Findings
        baseline = next((r for r in results if "Baseline" in r["name"]), None)
        optimized = next((r for r in results if "Optimized" in r["name"]), None)
        throughput = next((r for r in results if "Throughput" in r["name"]), None)

        if baseline and throughput:
            tps_drop = (
                ((baseline["tps"] - throughput["tps"]) / baseline["tps"] * 100)
                if baseline["tps"] > 0
                else 0
            )

            print(f"\n{'=' * 70}")
            print("FINDINGS")
            print(f"{'=' * 70}")
            print("Throughput optimization impact:")
            print(f"  TPS change: {tps_drop:+.1f}%")
            print(f"  Quality maintained: {baseline['quality_pass'] == throughput['quality_pass']}")

            if all(r["quality_pass"] for r in results):
                print("\n✓ All strategies produce quality outputs")
            else:
                print("\n⚠ Some strategies failed quality check")

        print(f"\nMETRIC quality_check_passed={sum(1 for r in results if r['quality_pass'])}")
        print(f"METRIC strategies_tested={len(results)}")


if __name__ == "__main__":
    asyncio.run(test_quality())
