"""Compare Ollama phi4 vs Lemonade Gemma-4 TPS."""

from __future__ import annotations

import time

import requests


def benchmark_ollama_phi4(prompt: str, max_tokens: int = 128) -> tuple[int, float]:
    """Returns (tokens, duration_seconds)."""
    start = time.time()
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "phi4:latest",
            "prompt": prompt,
            "system": "You are a concise assistant.",
            "options": {"num_predict": max_tokens},
            "stream": False,
        },
    )
    elapsed = time.time() - start
    data = resp.json()
    tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
    return tokens, elapsed


def main():
    prompts = [
        "Explain quantum computing in one sentence.",
        "Write a haiku about machine learning.",
        "What is 2+2?",
    ]

    print("=== Ollama phi4 (localhost:11434) ===")
    total_tokens = 0
    total_time = 0.0
    for prompt in prompts:
        tokens, elapsed = benchmark_ollama_phi4(prompt)
        tps = tokens / elapsed if elapsed > 0 else 0
        total_tokens += tokens
        total_time += elapsed
        print(f"  {prompt[:40]:40s} | Tokens: {tokens:3d} | Time: {elapsed:.2f}s | TPS: {tps:.1f}")

    avg_tps = total_tokens / total_time if total_time > 0 else 0
    print(f"  Average TPS: {avg_tps:.1f}")
    print(f"METRIC inference_tps={avg_tps:.1f}")


if __name__ == "__main__":
    main()
