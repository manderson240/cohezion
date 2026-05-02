#!/usr/bin/env python3
"""Test DeepSeek-R1 reasoning API structure for quality validation."""

import asyncio
import time

import aiohttp


async def test_reasoning_api():
    """Test DeepSeek-R1 with proper reasoning_format parameter."""

    base_url = "http://localhost:8002"
    model = "DeepSeek-R1-0528-Qwen3-8B-Q4_1.gguf"

    # Test different API formats
    tests = [
        {
            "name": "Standard chat (empty output)",
            "payload": {
                "model": model,
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "max_tokens": 50,
            },
        },
        {
            "name": "With reasoning_format=auto",
            "payload": {
                "model": model,
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "max_tokens": 50,
                "reasoning_format": "auto",  # DeepSeek specific
            },
        },
        {
            "name": "With reasoning content type",
            "payload": {
                "model": model,
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "max_tokens": 50,
                "temperature": 0.6,
            },
        },
        {
            "name": "Complex reasoning task",
            "payload": {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Solve step by step: If a train travels 120 miles in 2 hours, how fast is it going?",
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.6,
            },
        },
    ]

    async with aiohttp.ClientSession() as session:
        print("=" * 70)
        print("DEEPESEEK-R1 REASONING API TEST")
        print("=" * 70)
        print(f"Model: {model}\n")

        results = []

        for test in tests:
            print(f"\n{'=' * 70}")
            print(f"Test: {test['name']}")
            print(f"{'=' * 70}")

            start = time.time()
            try:
                async with session.post(
                    f"{base_url}/v1/chat/completions",
                    json=test["payload"],
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    elapsed = (time.time() - start) * 1000

                    # Check response structure
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    content = message.get("content", "")
                    reasoning = message.get("reasoning_content", "")

                    tokens = data.get("usage", {}).get("completion_tokens", 0)
                    tps = tokens / (elapsed / 1000) if elapsed > 0 else 0

                    print(f"Status: {resp.status}")
                    print(f"Time: {elapsed:.0f}ms")
                    print(f"Tokens: {tokens}")
                    print(f"TPS: {tps:.1f}")
                    print(
                        f"\nContent: '{content[:100]}...' "
                        if len(content) > 100
                        else f"\nContent: '{content}'"
                    )
                    if reasoning:
                        print(f"Reasoning: '{reasoning[:100]}...'")

                    # Quality check
                    has_output = len(content.strip()) > 0 or len(reasoning.strip()) > 0

                    results.append(
                        {
                            "name": test["name"],
                            "has_output": has_output,
                            "tps": tps,
                            "tokens": tokens,
                        }
                    )

                    print(f"\nHas output: {'✓' if has_output else '✗'}")

            except Exception as e:
                print(f"ERROR: {e}")
                results.append({"name": test["name"], "error": str(e)})

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")
        print(f"{'Test':<40} {'Has Output':<12} {'TPS':<10}")
        print("-" * 70)

        working = 0
        for r in results:
            if "error" not in r:
                status = "✓" if r["has_output"] else "✗"
                tps = f"{r['tps']:.1f}" if r["has_output"] else "N/A"
                print(f"{r['name']:<40} {status:<12} {tps:<10}")
                if r["has_output"]:
                    working += 1
            else:
                print(f"{r['name']:<40} ERROR")

        print(f"\n{'=' * 70}")
        print(f"Working configurations: {working}/{len(results)}")
        print(f"{'=' * 70}")

        print(f"\nMETRIC working_configs={working}")
        print(f"METRIC total_tests={len(results)}")

        return working


if __name__ == "__main__":
    result = asyncio.run(test_reasoning_api())
    exit(0 if result > 0 else 1)
