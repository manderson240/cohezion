#!/usr/bin/env python3
"""NPU Concurrent Benchmark - Maximize XDNA2 Throughput"""

import asyncio
import time

import aiohttp


async def benchmark_npu():
    print("Testing NPU with concurrent requests...")

    async with aiohttp.ClientSession() as session:
        # Warm-up
        print("Warming up...")
        await session.post(
            "http://localhost:8004/v1/chat/completions",
            json={
                "model": "gemma3:4b",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10,
            },
        )

        # Test concurrency levels
        for concurrency in [1, 2, 4]:
            print(f"\nTesting concurrency={concurrency}...")

            prompts = [f"Task {i}: Write a haiku" for i in range(concurrency)]
            start = time.time()

            tasks = []
            for p in prompts:
                tasks.append(
                    session.post(
                        "http://localhost:8004/v1/chat/completions",
                        json={
                            "model": "gemma3:4b",
                            "messages": [{"role": "user", "content": p}],
                            "max_tokens": 40,
                        },
                    )
                )

            responses = await asyncio.gather(*tasks)
            elapsed = (time.time() - start) * 1000

            total_tokens = 0
            for r in responses:
                data = await r.json()
                total_tokens += data.get("usage", {}).get("completion_tokens", 0)

            tps = total_tokens / (elapsed / 1000) if elapsed > 0 else 0
            print(
                f"  Concurrency={concurrency}: {tps:.1f} TPS ({total_tokens} tokens in {elapsed:.0f}ms)"
            )


if __name__ == "__main__":
    asyncio.run(benchmark_npu())
