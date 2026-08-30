#!/usr/bin/env python3
"""Consult Underutilized Cloud Models on Small Language Model (SLM) Swarms vs Single Monolithic Models on AMD Strix Halo (128GB UMA).

Evaluates:
1. Why an SLM Swarm (8-12 specialized models across NPU, iGPU, CPU) outperforms a single 120B model:
   - True Silicon Concurrency: NPU (FLM) + iGPU (Vulkan) + CPU (AVX-512) execute simultaneously without bus lock.
   - Ultra-High Decode Speeds: 8B models decode at 80-140 tok/s vs 30-40 tok/s for 120B.
   - Task Specialization: Dedicated Coder (Qwen-Coder), Reasoner (DeepSeek-R1-8B), Tool Agent (Gemma-4-E4B), Embedder (Nomic).
   - Zero Context Waste: No giant KV-cache penalty.
"""

import httpx

prompt = """You are a Principal AI Swarm Systems Architect.
Explain in 100 words why a Multi-SLM Swarm (e.g. Qwen3-8B Coder on iGPU + DeepSeek-R1-8B Reasoner on NPU + Gemma-E4B Tool Dispatcher + Nomic Embedder running concurrently) dramatically outperforms a single heavy 120B monolithic model on AMD Strix Halo (128GB Unified Memory, 50 TOPS XDNA2 NPU, Radeon 8060S iGPU).

Highlight:
1. True Heterogeneous Concurrency (NPU and iGPU compute in parallel).
2. Decoding Throughput (80-140 tok/s vs 30-40 tok/s).
3. Zero Memory Aperture Contention & Agentic Specialization."""

try:
    resp = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": "glm-5.3-flash:cloud", "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 300}},
        timeout=40.0
    )
    print("=" * 80)
    print("🐝 SLM SWARM VS MONOLITH ARCHITECTURAL SYNTHESIS")
    print("=" * 80)
    print(resp.json().get("response", "").strip())
    print("=" * 80)
except Exception as e:
    print(f"Notice: {e}")
