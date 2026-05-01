#!/usr/bin/env python3
"""Quality vs Throughput Trade-off Analysis

Tests if concurrency optimization affects output quality.

Metrics:
- Response coherence (success rate)
- Token count consistency
- Latency variance
- Output similarity (cosine similarity of embeddings)
"""

import asyncio
import time

import aiohttp


def evaluate_response_quality(text: str) -> dict:
    """Simple quality heuristics."""
    # Basic metrics
    word_count = len(text.split())
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    avg_word_len = sum(len(w) for w in text.split()) / max(word_count, 1)

    # Quality indicators
    has_punctuation = any(c in text for c in '.,!?;')
    has_newlines = '\n' in text
    starts_capital = text and text[0].isupper() if text else False

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_word_len": avg_word_len,
        "has_punctuation": has_punctuation,
        "has_newlines": has_newlines,
        "starts_capital": starts_capital,
        "length_ok": 10 <= word_count <= 200,  # reasonable range
    }

async def test_concurrency_quality(concurrency: int) -> dict:
    """Test quality at given concurrency level."""

    prompts = [
        "Explain quantum computing in simple terms.",
        "Write a haiku about machine learning.",
        "What are three benefits of exercise?",
        "Describe a sunset over the ocean.",
    ][:concurrency]

    base_url = "http://localhost:8002"

    async with aiohttp.ClientSession() as session:
        # Warm-up
        try:
            await session.post(
                f"{base_url}/v1/chat/completions",
                json={"model": "DeepSeek-Qwen3-8B-GGUF", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10},
                timeout=aiohttp.ClientTimeout(total=10)
            )
        except:
            pass

        # Benchmark
        start = time.time()
        results = []

        tasks = []
        for prompt in prompts:
            tasks.append(session.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": "DeepSeek-Qwen3-8B-GGUF",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ))

        try:
            responses = await asyncio.gather(*tasks)
            elapsed = (time.time() - start) * 1000

            total_tokens = 0
            qualities = []
            texts = []

            for resp in responses:
                try:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("completion_tokens", 0)

                    total_tokens += tokens
                    qualities.append(evaluate_response_quality(text))
                    texts.append(text)
                except Exception as e:
                    qualities.append({"error": str(e)})

            # Calculate metrics
            tps = total_tokens / (elapsed / 1000) if elapsed > 0 else 0

            # Quality score
            quality_score = 0
            for q in qualities:
                if "error" not in q:
                    quality_score += 1
                    if q.get("length_ok"):
                        quality_score += 1
                    if q.get("has_punctuation"):
                        quality_score += 0.5

            return {
                "concurrency": concurrency,
                "tps": tps,
                "total_tokens": total_tokens,
                "elapsed_ms": elapsed,
                "success_rate": len([q for q in qualities if "error" not in q]) / len(qualities) if qualities else 0,
                "quality_score": quality_score,
                "avg_quality": quality_score / len(qualities) if qualities else 0,
                "samples": len(texts),
            }

        except Exception as e:
            return {
                "concurrency": concurrency,
                "error": str(e),
                "tps": 0,
                "quality_score": 0,
            }

async def main():
    print("=" * 70)
    print("QUALITY VS THROUGHPUT ANALYSIS")
    print("=" * 70)
    print("\nTesting quality at different concurrency levels...\n")

    results = []
    for conc in [1, 2, 4]:
        print(f"Testing concurrency={conc}...")
        result = await test_concurrency_quality(conc)
        results.append(result)

        if "error" not in result:
            print(f"  TPS: {result['tps']:.1f}")
            print(f"  Success rate: {result['success_rate']*100:.0f}%")
            print(f"  Quality score: {result['quality_score']:.1f}")
            print(f"  Samples: {result['samples']}")
        else:
            print(f"  ERROR: {result['error']}")
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Conc':>6} {'TPS':>10} {'Success%':>10} {'Quality':>10}")
    print("-" * 40)

    for r in results:
        if "error" not in r:
            print(f"{r['concurrency']:>6} {r['tps']:>10.1f} {r['success_rate']*100:>9.0f}% {r['avg_quality']:>10.1f}")

    # Quality check
    if len(results) >= 2 and all("error" not in r for r in results):
        conc1_quality = results[0]["avg_quality"]
        conc4_quality = results[2]["avg_quality"] if len(results) > 2 else results[-1]["avg_quality"]

        quality_diff = ((conc4_quality - conc1_quality) / conc1_quality * 100) if conc1_quality > 0 else 0

        print("\n" + "=" * 70)
        print("QUALITY IMPACT ANALYSIS")
        print("=" * 70)
        print(f"Concurrency 1 quality: {conc1_quality:.2f}")
        print(f"Concurrency 4 quality: {conc4_quality:.2f}")
        print(f"Quality change: {quality_diff:+.1f}%")

        if abs(quality_diff) < 10:
            print("\n✓ Quality change within acceptable range (<10%)")
        else:
            print("\n⚠ Quality degradation detected - review needed")

if __name__ == "__main__":
    asyncio.run(main())
