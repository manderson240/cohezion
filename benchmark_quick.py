#!/usr/bin/env python3
"""Quick benchmark to confirm optimal throughput."""
import asyncio
import time

import aiohttp


async def main():
    url = "http://localhost:13307/v1/chat/completions"
    model = "DeepSeek-Qwen3-8B-GGUF"  # Will auto-detect

    # Detect model
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:13307/v1/models") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    if models:
                        model = models[0]
        except:
            pass

    connector = aiohttp.TCPConnector(limit=12, keepalive_timeout=300)

    async with aiohttp.ClientSession(connector=connector) as session:
        # Warm-up
        await session.post(url, json={
            "model": model,
            "messages": [{"role": "user", "content": "Say ready"}],
            "max_tokens": 10,
        })

        # 4 concurrent requests
        prompts = [f"Write a haiku about ML topic {i}." for i in range(4)]

        start = time.monotonic()
        tasks = [
            session.post(url, json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": p}
                ],
                "max_tokens": 40,
                "temperature": 0.7,
            })
            for p in prompts
        ]

        responses = await asyncio.gather(*tasks)

        total_tokens = 0
        for resp in responses:
            data = await resp.json()
            usage = data.get("usage", {})
            total_tokens += usage.get("completion_tokens", 0)

        elapsed_ms = (time.monotonic() - start) * 1000
        tps = total_tokens / (elapsed_ms / 1000)

        print(f"Model: {model}")
        print("Requests: 4 concurrent")
        print(f"Total tokens: {total_tokens}")
        print(f"Wall time: {elapsed_ms:.1f} ms")
        print(f"Throughput: {tps:.1f} TPS")
        print(f"\nMETRIC tokens_per_sec={tps:.1f}")
        print("METRIC concurrency=4")

        return tps

if __name__ == "__main__":
    tps = asyncio.run(main())
    exit(0 if tps > 0 else 1)
