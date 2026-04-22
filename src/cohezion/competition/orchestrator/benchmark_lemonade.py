"""Benchmark Lemonade throughput for Gemma-4-26B-A4B.

Measures tokens per second via the ModelDispatcher (OpenAI-compatible API).
"""
from __future__ import annotations

import time

from cohezion.competition.orchestrator.model_dispatcher import ModelDispatcher


def main():
    dispatcher = ModelDispatcher()

    # Warm up
    print("Warming up...")
    dispatcher.generate(
        "You are a concise assistant.",
        "Say 'hello' and nothing else.",
        max_tokens=10,
    )

    # Benchmark: multiple prompt lengths
    prompts = [
        "Explain quantum computing in one sentence.",
        "Write a haiku about machine learning.",
        "What is 2+2?",
    ]

    total_tokens = 0
    total_time = 0.0

    for prompt in prompts:
        start = time.time()
        result = dispatcher.generate(
            "You are a concise assistant.",
            prompt,
            max_tokens=128,
        )
        elapsed = time.time() - start
        tokens = result.tokens_used
        tps = tokens / elapsed if elapsed > 0 else 0
        total_tokens += tokens
        total_time += elapsed
        print(f"Prompt: {prompt[:40]:40s} | Tokens: {tokens:3d} | Time: {elapsed:.2f}s | TPS: {tps:.1f}")

    avg_tps = total_tokens / total_time if total_time > 0 else 0
    print(f"\nAverage TPS: {avg_tps:.1f}")
    print(f"METRIC inference_tps={avg_tps:.1f}")


if __name__ == "__main__":
    main()
