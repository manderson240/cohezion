#!/usr/bin/env python3
"""Consult Nemotron-3-Ultra on Optimal Multi-Silicon Hardware Mapping on AMD Strix Halo (128GB UMA).

Evaluates:
- NPU (XDNA2, 50 TOPS, INT8/MXFP4): Low-latency draft models, small vision/embeddings (embed-gemma, qwen3-0.6b, llama3.2-1b).
- iGPU (Radeon 8060S RDNA 3.5, 12GB+ UMA aperture, FP16/MXFP4): High-throughput MoE coding & reasoning (Qwen3.6-35B-A3B, Qwen3-8B, Muse-Glimmer-30B, Gemma-4-E4B).
- CPU (Ryzen 9 7945HX / AVX-512, 16C/32T): Granite 4.2 / Ornith 1.5 heavy context memory mapping.
"""

import httpx
import json

prompt = """You are a Principal Hardware Silicon Architect specializing in AMD Strix Halo (Ryzen AI MAX+ 395, 128GB LPDDR5X-7500 unified memory, XDNA2 NPU, Radeon 8060S iGPU).
Evaluate the optimal local substrate allocation for our newly discovered models (Granite-4.2 / Granite-tiny, Ornith-1.5, Muse-Glimmer-30B) alongside our active models (Qwen3.6-35B, Gemma-4-E4B, DeepSeek-Qwen3-8B):

1. Substrate Mapping across NPU vs iGPU vs CPU:
   - What belongs on NPU (INT8/FP4 low-latency token streaming)?
   - What belongs on iGPU (ROCm/Vulkan GGUF compute-bound matrix math)?
   - What belongs on CPU (large AVX-512 memory-bound tree search & KV caching)?
2. Where do Granite-4.2, Ornith-1.5, and Muse-Glimmer-30B fit best?

Provide a crisp, actionable hardware allocation table under 200 words."""

try:
    resp = httpx.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "nemotron-3-ultra:cloud",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 450}
        },
        timeout=40.0
    )
    if resp.status_code == 200:
        print("🖥️ AMD STRIX HALO MULTI-SILICON SUBSTRATE ALLOCATION:")
        print("=" * 80)
        print(resp.json().get("response", ""))
        print("=" * 80)
    else:
        print(f"HTTP {resp.status_code}")
except Exception as e:
    print(f"Notice: {e}")
