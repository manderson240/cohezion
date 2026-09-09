#!/usr/bin/env python3
"""Consult Underutilized Cloud Models on Scaling Local Memory Utilization on AMD Strix Halo (128GB UMA).

Evaluates:
1. Why does `free -h` show 97GiB used right now? (ZFS 16GB ARC + KV Caches for 262k/131k context windows + Model weights).
2. How can we allocate larger model architectures (e.g. 70B Q4 / 35B MoE at higher precision Q8 / 80B A3B) to utilize up to 100-110GB of our 128GB unified RAM safely?
"""

import httpx

prompt = """You are a Principal AI Hardware Systems Architect.
On our AMD Strix Halo (128GB Unified Memory, Ryzen AI MAX+ 395), `free -h` currently shows:
Total: 122Gi, Used: 97Gi (ZFS ARC 16GB + loaded model KV caches at 262k/131k context + weights), Available: 25Gi.

Explain in 100 words:
1. Why large KV-cache allocations (e.g. 262,144 context on Gemma-4-26B) consume 30-50GB of RAM on top of raw model weights.
2. How we can scale model weight memory (e.g. loading 70B/80B models or Qwen3.6-35B at Q8_0) by capping context windows to 16k/32k to utilize 100+ GB of RAM for model intelligence rather than empty context buffers."""

try:
    resp = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": "gpt-oss:120b-cloud", "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 300}},
        timeout=40.0
    )
    print("=" * 80)
    print("🧠 CLOUD ARCHITECT ANALYSIS: MEMORY ALLOCATION & KV-CACHE SCALING")
    print("=" * 80)
    print(resp.json().get("response", "").strip())
    print("=" * 80)
except Exception as e:
    print(f"Notice: {e}")
