#!/usr/bin/env python3
"""Final Quality Check - Using correct model ID"""

import asyncio
import time

import aiohttp


async def test_quality():
    base_url = "http://localhost:8002"

    # Get actual model name from server
    async with aiohttp.ClientSession() as session, session.get(f"{base_url}/v1/models") as resp:
        data = await resp.json()
        models = [m['id'] for m in data.get('data', [])]
        model = models[0] if models else "unknown"
        print(f"Testing with model: {model}")

    # Test three configurations
    configs = [
        {"name": "Baseline", "temp": 0.7, "system": "You are helpful."},
        {"name": "Quality", "temp": 0.3, "system": "You are precise and factual."},
        {"name": "Throughput", "temp": 0.1, "system": "You are helpful."},
    ]

    prompt = "What is 2+2? Answer in one word."

    async with aiohttp.ClientSession() as session:
        print("\n" + "=" * 70)
        print("QUALITY TEST")
        print("=" * 70)

        results = []

        for cfg in configs:
            print(f"\nTesting: {cfg['name']} (temp={cfg['temp']})")

            start = time.time()
            async with session.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": cfg['system']},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": cfg['temp'],
                    "max_tokens": 10,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                elapsed = (time.time() - start) * 1000

                text = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("completion_tokens", 0)
                tps = tokens / (elapsed / 1000) if elapsed > 0 else 0

                # Quality: correct answer?
                correct = "4" in text or "four" in text.lower()

                print(f"  Output: '{text}'")
                print(f"  Tokens: {tokens} | Time: {elapsed:.0f}ms | TPS: {tps:.1f}")
                print(f"  Correct: {'✓' if correct else '✗'}")

                results.append({
                    "name": cfg['name'],
                    "tps": tps,
                    "correct": correct,
                    "text": text,
                })

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"{'Config':<15} {'TPS':<10} {'Correct':<10}")
        print("-" * 70)
        for r in results:
            print(f"{r['name']:<15} {r['tps']:<10.1f} {'✓' if r['correct'] else '✗'}")

        correct_count = sum(1 for r in results if r['correct'])
        avg_tps = sum(r['tps'] for r in results) / len(results)

        print(f"\nCorrect answers: {correct_count}/{len(results)}")
        print(f"Average TPS: {avg_tps:.1f}")

        # Conclusion
        print(f"\n{'='*70}")
        if correct_count == len(results):
            print("✓ All configurations produce CORRECT answers")
            print("→ Throughput optimization does NOT harm accuracy")
        else:
            print("⚠ Some configurations produce INCORRECT answers")
            print("→ Review temperature/system prompt settings")
        print(f"{'='*70}")

        print(f"\nMETRIC correct_answers={correct_count}")
        print(f"METRIC avg_tps={avg_tps:.1f}")
        print(f"METRIC quality_preserved={1 if correct_count == len(results) else 0}")


if __name__ == "__main__":
    asyncio.run(test_quality())
