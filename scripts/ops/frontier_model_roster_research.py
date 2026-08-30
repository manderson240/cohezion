#!/usr/bin/env python3
"""Bleeding-Edge Model Architecture Research: Consult Ollama Cloud models on optimal NPU, iGPU, and CPU model rosters for AMD Strix Halo & Lemonade Server."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


out_report = Path("/home/mike-anderson/dev/cohezion/docs/research/bleeding_edge_model_roster_research_2026.md")
out_report.parent.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    print("=" * 90)
    print("  🔬 BLEEDING-EDGE MODEL ROSTER RESEARCH: STRIX HALO (NPU / iGPU / CPU)")
    print("=" * 90)

    router = UnifiedHybridRouter()

    prompt = """
You are a Principal Hardware-Aware AI Systems Architect specializing in AMD Strix Halo (Ryzen AI MAX+ 395 w/ Radeon 8060S, 128GB Unified LPDDR5X-7500, XDNA2 NPU, RDNA 3.5 iGPU, Zen 5 CPU).

Our Current Local Lemonade Server Roster (:13305):
- NPU (FastLane / flm): `qwen3.6-moe-35b-a3b-FLM` (35B/3B active), `waslmedia-qwen3-4b`, `deepseek-r1-0528-8b-FLM`, `llama3.2-1b-FLM`.
- iGPU (Vulkan / ROCm llamacpp): `Qwen3-Coder-30B-A3B-Instruct-GGUF`, `Bonsai-27B-gguf-Q1_0`, `DeepSeek-V4-Flash-0731-UD-Q8_K_XL`.
- CPU (AVX-512 / Zen 5): `Gemma-4-31B-it-GGUF`, `gpt-oss-20b-mxfp4-GGUF`, `Mistral-Medium-3.5-128B-IQ4_KT`.
- Multimodal / Vision: `qwen3vl-it-4b-FLM`, `SD-Turbo`, `TRELLIS-3D`.

Research & recommend the most optimal, bleeding-edge open-weights model architectures released in 2026 across each silicon tier:

1. NPU Optimization (XDNA2 50 TOPS, FastLane/FLM format):
   - What new ultra-sparse MoE (e.g. 15B-35B A2B/A3B) or dynamic routing architectures exist that maximize NPU throughput while staying under 25 GB memory footprint?
   - Any new MTP (Multi-Token Prediction) or speculative decoding drafters optimized for NPU?

2. iGPU Optimization (Radeon 8060S, 40 CUs, RDNA 3.5, shared UMA VRAM):
   - Which coding and agentic models outperform Qwen3-Coder-30B (e.g. Devstral-2, Qwen3.8-35B-Coder, GLM-Coder, DeepSeek-Coder-V3)?
   - Optimal quantization formats (e.g. MXFP4, IQ3_XS, Q5_K_M) for maximizing decode throughput (>90 tok/s) while preserving 100% HumanEval/SWE-bench accuracy?

3. CPU Optimization (16-core / 32-thread Zen 5, AVX-512, huge context):
   - For long-horizon architecture, complex synthesis, and 1M+ context windows where iGPU VRAM is reserved, what are the top CPU models?

4. Unified Custom Lemonade Router Policy Architecture:
   - Provide an updated, optimal routing matrix mapping specific prompt intents to the highest ROI models across the 3 silicon domains.
"""

    models_to_query = [
        ("deepseek-v4-pro:cloud", "DeepSeek-V4 Pro (Frontier Architecture & Reasoning Specialist)"),
        ("glm-5.2:cloud", "GLM-5.2 (Frontier Hardware & Open-Weights Specialist)")
    ]

    responses = {}
    for model_id, label in models_to_query:
        print(f"\nConsulting {label} ({model_id})...")
        t0 = time.perf_counter()
        try:
            content = await router.aquery_ollama_cloud(prompt=prompt, model=model_id)
            dt = time.perf_counter() - t0
            print(f"  ✓ Received response in {dt:.2f}s ({len(content or '')} chars)")
            responses[model_id] = {
                "label": label,
                "content": content,
                "latency_s": dt
            }
        except Exception as e:
            print(f"  ✗ Error querying {model_id}: {e}")

    report = f"""# Bleeding-Edge Model Roster Research (Strix Halo NPU / iGPU / CPU)

**Research Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Target Architecture**: AMD Strix Halo (AMD Ryzen AI MAX+ 395 w/ Radeon 8060S, 128GB Unified Memory)  
**Inference Engine**: Lemonade OmniRouter (port `13305`)  

---

"""
    for mid, data in responses.items():
        report += f"## Perspective: {data['label']}\n\n"
        report += f"{data['content']}\n\n---\n\n"

    with open(out_report, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✓ Master Research Report saved to: {out_report} ({out_report.stat().st_size} bytes)")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())
