#!/usr/bin/env python3
"""Direct fast query to Qwen3.5-397B on port 11434."""

import json
import time
import urllib.request


prompt = """
You are a Principal AI Kernel & Systems Architect reviewing an AMD Strix Halo deployment (AMD Ryzen AI MAX+ 395 w/ Radeon 8060S, 128GB Unified LPDDR5X-7500, 210 GB/s bandwidth, XDNA2 NPU @ 50 TOPS, RDNA 3.5 iGPU 40 CUs, Zen 5 CPU).

Current setup:
- NPU: qwen3.6-moe-35b-a3b (FLM) + waslmedia-4b + embed-gemma-300m
- iGPU: Qwen3-Coder-30B-A3B (88.1 tok/s decode, 128k ctx) + gpt-oss-20b-MXFP4
- CPU: Mistral-Medium-128B-IQ4_KT + lfm25-embed-350m (1024D)
- Audio: Whisper-Large-v3-Turbo + kokoro-v1

How can we push this system even further to get maximum throughput and intelligence? Detail 4 breakthrough optimizations for this 128GB APU architecture.
"""

payload = {
    "model": "qwen3.5:397b-cloud",
    "prompt": prompt,
    "stream": False
}

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

print("Querying qwen3.5:397b-cloud directly on port 11434...")
t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        dt = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        res = data.get("response", "")
        print(f"✓ Received response in {dt:.2f}s ({len(res)} chars):")
        with open("/home/mike-anderson/dev/cohezion/docs/research/frontier_qwen397b_optimization_findings.md", "w", encoding="utf-8") as f:
            f.write("# Qwen3.5-397B Frontier Hardware Optimization Review\n\n")
            f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("**Target System**: AMD Ryzen AI MAX+ 395 (Strix Halo)\n\n---\n\n")
            f.write(res)
        print("✓ Saved findings to docs/research/frontier_qwen397b_optimization_findings.md")
except Exception as e:
    print(f"✗ Direct query error: {e}")
