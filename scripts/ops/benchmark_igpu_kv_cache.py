#!/usr/bin/env python3
"""Benchmark Qwen3-Coder-30B KV-cache reuse on Radeon 8060S iGPU (llama.cpp engine)."""

import json
import time
import urllib.request


url = "http://localhost:13305/v1/chat/completions"
model = "Qwen3-Coder-30B-A3B-Instruct-GGUF"

# System prompt with long codebase context
PREFIX = "You are an expert software engineer. Here is the repository context: " + ("// System invariant verified.\n" * 100)

def run_turn(turn: int, prompt: str):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PREFIX},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 30
    }
    req = urllib.request.Request(
        url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        dt = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        timings = data.get("timings", {})
        prompt_ms = timings.get("prompt_ms", 0.0)
        prompt_n = timings.get("prompt_n", 0)
        prompt_tps = timings.get("prompt_per_second", 0.0)
        print(f"Turn {turn}: Total = {dt*1000:.1f}ms | Prefill = {prompt_ms:.1f}ms ({prompt_n} tokens @ {prompt_tps:.1f} tok/s)")

print("=== Benchmarking iGPU KV-Cache Prefix Reuse ===")
run_turn(1, "What is function A?")
run_turn(2, "What is function B?")
run_turn(3, "What is function C?")
