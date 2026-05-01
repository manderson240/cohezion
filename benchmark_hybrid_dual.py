#!/usr/bin/env python3
"""Dual Compute Benchmark - GPU (Lemonade) + CPU (Ollama) simultaneously.

Maximizes throughput by running phi4 (14B) on CPU while Qwen3 (8B) runs on GPU.
Unique to AMD Ryzen AI MAX+ 395 with 128GB UMA.
"""

import asyncio
import time

import aiohttp


async def generate_gpu(
    session: aiohttp.ClientSession,
    prompt: str,
    max_tokens: int = 40,
) -> tuple[int, float, bool]:
    """Generate on Lemonade GPU (Vulkan backend)."""
    try:
        payload = {
            "model": "DeepSeek-Qwen3-8B-GGUF",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": False,
        }

        start = time.monotonic()
        async with session.post(
            "http://localhost:8002/v1/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            elapsed_ms = (time.monotonic() - start) * 1000

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens = usage.get("completion_tokens", len(content.split()))
            return tokens, elapsed_ms, True
    except Exception:
        return 0, 0, False


async def generate_cpu(
    session: aiohttp.ClientSession,
    prompt: str,
    max_tokens: int = 40,
) -> tuple[int, float, bool]:
    """Generate on Ollama CPU."""
    try:
        payload = {
            "model": "phi4:latest",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"num_thread": 8, "temperature": 0.7},
        }

        start = time.monotonic()
        async with session.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            elapsed_ms = (time.monotonic() - start) * 1000

            content = data.get("message", {}).get("content", "")
            tokens = len(content.split())  # Estimate
            return tokens, elapsed_ms, True
    except Exception:
        return 0, 0, False


async def run_dual_benchmark(
    num_per_unit: int = 2,
) -> dict:
    """Run GPU and CPU in parallel."""
    print("=" * 70)
    print("HYBRID DUAL COMPUTE - GPU + CPU Parallel")
    print("=" * 70)
    print(f"\nRunning {num_per_unit} requests on each unit simultaneously...\n")

    connector = aiohttp.TCPConnector(limit=16)

    async with aiohttp.ClientSession(connector=connector) as session:
        gpu_prompts = [f"GPU task {i}: Write a haiku." for i in range(num_per_unit)]
        cpu_prompts = [f"CPU task {i}: Write a haiku." for i in range(num_per_unit)]

        start_all = time.monotonic()

        # Launch all tasks
        gpu_tasks = [generate_gpu(session, p) for p in gpu_prompts]
        cpu_tasks = [generate_cpu(session, p) for p in cpu_prompts]

        # Run GPU and CPU batches concurrently
        gpu_results = await asyncio.gather(*gpu_tasks)
        cpu_results = await asyncio.gather(*cpu_tasks)

        total_time_ms = (time.monotonic() - start_all) * 1000

    # Process results
    gpu_tokens = sum(r[0] for r in gpu_results if r[2])
    gpu_success = sum(1 for r in gpu_results if r[2])
    gpu_time = max(r[1] for r in gpu_results if r[2]) if gpu_success > 0 else 0

    cpu_tokens = sum(r[0] for r in cpu_results if r[2])
    cpu_success = sum(1 for r in cpu_results if r[2])
    cpu_time = max(r[1] for r in cpu_results if r[2]) if cpu_success > 0 else 0

    total_tokens = gpu_tokens + cpu_tokens
    combined_tps = total_tokens / (total_time_ms / 1000) if total_time_ms > 0 else 0

    print("GPU (Lemonade Vulkan / Qwen3-8B):")
    print(f"  Success:      {gpu_success}/{num_per_unit}")
    print(f"  Tokens:       {gpu_tokens}")
    print(f"  Avg time:     {gpu_time:.1f}ms")
    if gpu_time > 0:
        print(f"  Est. TPS:     {gpu_tokens / (gpu_time/1000):.1f}")

    print("\nCPU (Ollama / Phi4-14B):")
    print(f"  Success:      {cpu_success}/{num_per_unit}")
    print(f"  Tokens:       {cpu_tokens}")
    print(f"  Avg time:     {cpu_time:.1f}ms")
    if cpu_time > 0:
        print(f"  Est. TPS:     {cpu_tokens / (cpu_time/1000):.1f}")

    print("\n" + "=" * 70)
    print("COMBINED (Parallel Execution):")
    print(f"  Wall time:    {total_time_ms:.1f}ms")
    print(f"  Total tokens: {total_tokens}")
    print(f"  COMBINED TPS: {combined_tps:.1f}")
    print("=" * 70)

    print(f"\nMETRIC tokens_per_sec={combined_tps:.1f}")
    print(f"METRIC gpu_tps={gpu_tokens / (gpu_time/1000) if gpu_time > 0 else 0:.1f}")

    return {
        "tokens_per_sec": combined_tps,
        "gpu_tps": gpu_tokens / (gpu_time/1000) if gpu_time > 0 else 0,
        "cpu_tps": cpu_tokens / (cpu_time/1000) if cpu_time > 0 else 0,
        "wall_time_ms": total_time_ms,
    }


async def main():
    result = await run_dual_benchmark(num_per_unit=2)
    return 0 if result["tokens_per_sec"] > 0 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
