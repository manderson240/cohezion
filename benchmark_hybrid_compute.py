#!/usr/bin/env python3
"""Hybrid Compute Benchmark - Utilize CPU, GPU, and NPU simultaneously.

Routes requests to optimal compute unit:
- CPU (Zen 5): Small models (<3B) - lowest TTFT
- GPU (Vulkan): Medium models (3B-14B) - highest throughput  
- NPU (XDNA2): Quantized models - 60-80 TOPS potential

Based on MultiModelOrchestrator compute profiles.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum

import aiohttp


class ComputeUnit(Enum):
    CPU = "cpu"
    GPU = "gpu"
    NPU = "npu"


@dataclass
class ModelProfile:
    name: str
    size_b: float
    preferred_unit: ComputeUnit
    endpoint: str
    model_id: str


# Model routing based on empirical profiles
COMPUTE_PROFILES = {
    # Small models - CPU optimal (low latency)
    "phi3:mini": ModelProfile("phi3:mini", 3.8, ComputeUnit.CPU, "http://localhost:11434", "phi3:mini"),
    "llama3.2:1b": ModelProfile("llama3.2:1b", 1.0, ComputeUnit.CPU, "http://localhost:11434", "llama3.2:1b"),

    # Medium models - GPU optimal (Vulcan backend)
    "qwen3-8b": ModelProfile("qwen3-8b", 8.0, ComputeUnit.GPU, "http://localhost:8002", "DeepSeek-Qwen3-8B-GGUF"),
    "phi4:latest": ModelProfile("phi4:latest", 3.8, ComputeUnit.GPU, "http://localhost:11434", "phi4:latest"),

    # NPU - Would need quantized ONNX models
    # "phi3:npu": ModelProfile("phi3:npu", 3.8, ComputeUnit.NPU, "http://localhost:8001", "phi3:npu"),
}


async def generate_on_unit(
    session: aiohttp.ClientSession,
    profile: ModelProfile,
    prompt: str,
    system: str = "You are a helpful assistant.",
    max_tokens: int = 128,
) -> tuple[int, float, bool, ComputeUnit]:
    """Generate on specific compute unit."""

    if profile.preferred_unit == ComputeUnit.CPU:
        # Ollama CPU endpoint
        payload = {
            "model": profile.model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"num_thread": 8, "temperature": 0.7},
        }
        url = f"{profile.endpoint}/api/chat"
    else:
        # Lemonade GPU endpoint (OpenAI compatible)
        payload = {
            "model": profile.model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": False,
        }
        url = f"{profile.endpoint}/v1/chat/completions"

    start = time.monotonic()
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            data = await resp.json()
            elapsed_ms = (time.monotonic() - start) * 1000

            if profile.preferred_unit == ComputeUnit.CPU:
                # Ollama format
                content = data.get("message", {}).get("content", "")
                tokens = len(content.split())  # Estimate
            else:
                # OpenAI format
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                tokens = usage.get("completion_tokens", len(content.split()))

            return tokens, elapsed_ms, True, profile.preferred_unit
    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000
        return 0, elapsed_ms, False, profile.preferred_unit


async def benchmark_single_unit(
    unit: ComputeUnit,
    num_requests: int = 4,
) -> dict:
    """Benchmark a single compute unit."""

    # Select appropriate profile for unit
    if unit == ComputeUnit.CPU:
        profile = COMPUTE_PROFILES["llama3.2:1b"]  # 1B model for CPU
    elif unit == ComputeUnit.GPU:
        profile = COMPUTE_PROFILES["qwen3-8b"]  # 8B model for GPU
    else:
        return {"error": "NPU not available", "tps": 0}

    print(f"  Benchmarking {unit.value.upper()} with {profile.name}...")

    connector = aiohttp.TCPConnector(limit=8)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Check if endpoint available
        try:
            if unit == ComputeUnit.GPU:
                async with session.get(f"{profile.endpoint}/v1/models", timeout=5):
                    pass
            else:
                async with session.get(f"{profile.endpoint}/api/tags", timeout=5):
                    pass
        except Exception as e:
            return {"error": f"Endpoint not available: {e}", "tps": 0}

        prompts = [f"Write a haiku about topic {i}." for i in range(num_requests)]

        start = time.monotonic()
        tasks = [generate_on_unit(session, profile, p) for p in prompts]
        results = await asyncio.gather(*tasks)
        elapsed_ms = (time.monotonic() - start) * 1000

        total_tokens = sum(r[0] for r in results if r[2])
        successful = sum(1 for r in results if r[2])
        tps = total_tokens / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

        return {
            "unit": unit.value,
            "model": profile.name,
            "tps": tps,
            "total_tokens": total_tokens,
            "elapsed_ms": elapsed_ms,
            "successful": successful,
        }


async def benchmark_hybrid_parallel(
    num_per_unit: int = 4,
) -> dict:
    """Run all compute units in parallel for aggregate throughput."""

    print("=" * 70)
    print("HYBRID COMPUTE BENCHMARK - CPU + GPU + NPU")
    print("=" * 70)
    print("\nRunning units in parallel...\n")

    # Start all benchmarks concurrently
    tasks = []

    # CPU benchmark
    tasks.append(benchmark_single_unit(ComputeUnit.CPU, num_per_unit))

    # GPU benchmark
    tasks.append(benchmark_single_unit(ComputeUnit.GPU, num_per_unit))

    # NPU (check if available)
    # tasks.append(benchmark_single_unit(ComputeUnit.NPU, num_per_unit))

    results = await asyncio.gather(*tasks)

    # Aggregate results
    total_tokens = sum(r.get("total_tokens", 0) for r in results)
    max_time_ms = max(r.get("elapsed_ms", 0) for r in results)

    aggregate_tps = total_tokens / (max_time_ms / 1000) if max_time_ms > 0 else 0

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    for r in results:
        if "error" in r:
            print(f"\n{r.get('unit', 'UNKNOWN').upper()}: ERROR - {r['error']}")
        else:
            print(f"\n{r['unit'].upper()} ({r['model']}):")
            print(f"  Throughput:   {r['tps']:.1f} TPS")
            print(f"  Tokens:       {r['total_tokens']}")
            print(f"  Successful:   {r['successful']}/{num_per_unit}")

    print("\n" + "-" * 70)
    print("AGGREGATE (parallel execution):")
    print(f"  Total tokens:  {total_tokens}")
    print(f"  Wall time:     {max_time_ms:.1f} ms")
    print(f"  Combined TPS:    {aggregate_tps:.1f}")
    print("=" * 70)

    print(f"\nMETRIC tokens_per_sec={aggregate_tps:.1f}")
    print(f"METRIC cpu_tps={results[0].get('tps', 0):.1f}")
    print(f"METRIC gpu_tps={results[1].get('tps', 0):.1f}")

    return {
        "aggregate_tps": aggregate_tps,
        "cpu_tps": results[0].get("tps", 0),
        "gpu_tps": results[1].get("tps", 0),
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--requests", type=int, default=4)
    args = parser.parse_args()

    result = await benchmark_hybrid_parallel(args.requests)
    return 0 if result["aggregate_tps"] > 0 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
