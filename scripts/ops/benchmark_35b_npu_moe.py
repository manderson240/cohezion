#!/usr/bin/env python3
"""Benchmark and verify Qwen 35B MoE on AMD XDNA2 NPU via Lemonade FastLane (recipe: flm)."""

from __future__ import annotations

import json
import time
import urllib.request


url = "http://localhost:13305/v1/chat/completions"
model_id = "qwen3.6-moe-35b-a3b-FLM"

print(f"Testing direct inference on {model_id} (recipe: flm / XDNA2 NPU)...")

payload = {
    "model": model_id,
    "messages": [
        {"role": "system", "content": "You are an expert AGI engineer operating on AMD Strix Halo NPU."},
        {"role": "user", "content": "Explain in 2 sentences how a 35B MoE model with 3B active parameters achieves near-30B intelligence at 3B compute latency."}
    ],
    "max_tokens": 100,
    "temperature": 0.3
}

req = urllib.request.Request(
    url,
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        dt = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        timings = data.get("timings", {})
        print(f"✓ Inference succeeded in {dt:.2f}s!")
        print(f"  Model: {data.get('model')}")
        print(f"  Timings: {timings}")
        content = data["choices"][0]["message"]["content"]
        reasoning = data["choices"][0]["message"].get("reasoning_content", "")
        print(f"  Response: {content or reasoning}")
except Exception as e:
    print(f"✗ Direct inference error: {e}")
