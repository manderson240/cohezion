#!/usr/bin/env python3
"""Direct query to GLM-5.2 cloud model with explicit timeout and error tracing."""

import json
import time
import urllib.request


prompt = """
You are a Principal Hardware-Aware AI Systems Architect specializing in AMD Strix Halo (Ryzen AI MAX+ 395 w/ Radeon 8060S, 128GB Unified Memory, XDNA2 NPU, RDNA 3.5 iGPU, Zen 5 CPU).

Our Current Local Lemonade Server Roster (:13305):
- NPU (FastLane / flm): `qwen3.6-moe-35b-a3b-FLM` (35B/3B active), `waslmedia-qwen3-4b`, `deepseek-r1-0528-8b-FLM`, `llama3.2-1b-FLM`.
- iGPU (Vulkan / ROCm llamacpp): `Qwen3-Coder-30B-A3B-Instruct-GGUF`, `Bonsai-27B-gguf-Q1_0`, `DeepSeek-V4-Flash-0731-UD-Q8_K_XL`.
- CPU (AVX-512 / Zen 5): `Gemma-4-31B-it-GGUF`, `gpt-oss-20b-mxfp4-GGUF`, `Mistral-Medium-3.5-128B-IQ4_KT`.
- Multimodal / Vision: `qwen3vl-it-4b-FLM`, `SD-Turbo`, `TRELLIS-3D`.

Evaluate and recommend the bleeding-edge open-weights model upgrades across each silicon tier:
1. NPU (XDNA2): Should we stay with Qwen3.6-35B-A3B or adopt newer MTP (Multi-Token Prediction) variants like `Qwen3.6-35B-A3B-MTP`?
2. iGPU (Radeon 8060S): Compare Qwen3-Coder-30B against `Nemotron-3-Nano-30B-A3B`, `DeepSeek-V4-Flash-0731-UD-Q8_K_XL`, and `Qwen3.8-27B-GGUF-Q4_K_M`. Which gives >85 tok/s decode with highest coding accuracy?
3. CPU (Zen 5 AVX-512): Best models for massive context (>256k tokens) when VRAM is reserved for vision/diffusion?
4. Lemonade Router Policy: Recommended updated routing matrix.
"""

payload = {
    "model": "glm-5.2:cloud",
    "prompt": prompt,
    "stream": False
}

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

print("Querying GLM-5.2 cloud model directly on port 11434...")
t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        dt = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        res_text = data.get("response", "")
        print(f"✓ Received response in {dt:.2f}s ({len(res_text)} chars):")
        with open("/home/mike-anderson/dev/cohezion/docs/research/bleeding_edge_model_roster_research_2026.md", "w", encoding="utf-8") as f:
            f.write("# Bleeding-Edge Hardware-Aligned Model Roster (AMD Strix Halo)\n\n")
            f.write(f"**Research Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("**Target Processor**: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (128GB Unified Memory)\n\n---\n\n")
            f.write(res_text)
        print("✓ Report saved to docs/research/bleeding_edge_model_roster_research_2026.md")
except Exception as e:
    print(f"✗ Direct query error: {e}")
