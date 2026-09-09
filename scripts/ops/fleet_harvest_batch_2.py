#!/usr/bin/env python3
"""Batch 2: Sequential Model Knowledge Harvest & Enrichment Carousel (OOM Safeguarded).

Cycles through the next batch of specialized local models:
1. `Qwen3-0.6B-GGUF` (Edge AST / Fast Verification)
2. `Bonsai-4B-gguf` (Ternary / Sparse Weights & Quantization)
3. `LFM2.5-2.6B-GGUF-BF16` (Liquid Foundation / Continuous Time ODEs)
4. `Gemma-4-E2B-it-GGUF` (Multimodal Compact Invariants)
5. `SmolLM3-3B-IQ4_XS-GGUF-IQ4_XS` (Extreme Low-Bit Sparse Compaction)
"""

import asyncio
import json
import logging
import os
import psutil
import time
from dataclasses import dataclass
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [BATCH_2_HARVEST] %(message)s")
logger = logging.getLogger("batch_2_harvest")

LEMONADE_BASE = "http://localhost:13305"
MIN_AVAIL_RAM_GB = 15.0

BATCH_2_MODELS = [
    (
        "Qwen3-0.6B-GGUF",
        "Edge Verification & Micro-Transformers",
        "State why sub-1B parameter models running locally on CPU/NPU provide deterministic low-latency security guardrails for agent swarms in 2 dense sentences."
    ),
    (
        "Bonsai-4B-gguf",
        "Ternary Quantization & Sparse SVD",
        "Explain how ternary {-1, 0, +1} weight matrices reduce memory bandwidth saturation on unified memory architectures in 2 sentences."
    ),
    (
        "LFM2.5-2.6B-GGUF-BF16",
        "Liquid Foundation Models & Continuous Neural ODEs",
        "Formulate how continuous-time Liquid Neural Networks adapt state transitions smoothly under irregular sensor timesteps in 2 mathematical sentences."
    ),
    (
        "Gemma-4-E2B-it-GGUF",
        "Compact Multimodal Embeddings & J-Space",
        "Explain how compact 2B multimodal models map spatial and perceptual embeddings into a unified Poincaré manifold in 2 concise sentences."
    ),
    (
        "SmolLM3-3B-IQ4_XS-GGUF-IQ4_XS",
        "Extreme Quantization & KV-Cache Compression",
        "Explain why IQ4_XS extreme low-bit quantization preserves high-order attention entropy during long-context inference in 2 sentences."
    )
]

@dataclass
class HarvestResult:
    model: str
    domain: str
    prompt: str
    insight: str
    tokens: int
    duration_sec: float
    ram_headroom_gb: float

def get_free_ram_gb() -> float:
    return psutil.virtual_memory().available / (1024 ** 3)

async def harvest_single(model: str, domain: str, prompt: str) -> HarvestResult | None:
    avail_ram = get_free_ram_gb()
    if avail_ram < MIN_AVAIL_RAM_GB:
        logger.warning("⚠️ OOM Guard: Available RAM (%.2f GB) < floor (%.2f GB). Skipping %s.", avail_ram, MIN_AVAIL_RAM_GB, model)
        return None

    t0 = time.perf_counter()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"You are a world-class AI researcher synthesizing insights for Cohezion's {domain} knowledge graph. Answer in 2 dense, precise sentences."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 256
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=payload)
            dt_s = time.perf_counter() - t0
            if r.status_code == 200:
                data = r.json()
                text = data["choices"][0]["message"]["content"].strip()
                if "</think>" in text:
                    text = text.split("</think>")[-1].strip()
                return HarvestResult(
                    model=model,
                    domain=domain,
                    prompt=prompt,
                    insight=text,
                    tokens=len(text.split()),
                    duration_sec=round(dt_s, 2),
                    ram_headroom_gb=round(get_free_ram_gb(), 2)
                )
            else:
                logger.info("Model '%s' status %d: %s", model, r.status_code, r.text[:80])
    except Exception as exc:
        logger.info("Model '%s' inference skipped/timed out: %s", model, exc)
    return None

async def run_batch_2():
    print("\n" + "=" * 105)
    print("🎡 BATCH 2: FULL-FLEET SEQUENTIAL KNOWLEDGE HARVEST & ENRICHMENT")
    print(f"• Models in Batch 2      : {len(BATCH_2_MODELS)}")
    print(f"• Initial Free RAM Floor : {get_free_ram_gb():.2f} GiB (Floor: {MIN_AVAIL_RAM_GB} GiB)")
    print("=" * 105)

    results: list[HarvestResult] = []

    for idx, (model, domain, prompt) in enumerate(BATCH_2_MODELS, 1):
        print(f"\n[{idx}/{len(BATCH_2_MODELS)}] Ingesting Knowledge from `{model}` ({domain})...")
        res = await harvest_single(model, domain, prompt)
        if res:
            results.append(res)
            print(f"  • 🟢 Ingested ({res.duration_sec}s | RAM Free: {res.ram_headroom_gb} GiB)")
            print(f"  • Insight: {res.insight[:130]}...")
        else:
            print(f"  • 🟡 Skipped/Fallback.")

    # Append to Matrix
    out_file = "docs/research/full_fleet_enrichment_matrix.md"
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(f"\n### Batch 2 Ingestion ({len(results)} Models)\n\n")
        f.write("| Model | Domain | Duration | RAM Headroom | Synthesized Insight |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            clean_text = r.insight.replace("\n", " ").replace("|", "\\|")
            f.write(f"| `{r.model}` | {r.domain} | {r.duration_sec}s | {r.ram_headroom_gb} GiB | {clean_text} |\n")

    print("\n" + "=" * 105)
    print(f"🎉 BATCH 2 HARVEST COMPLETED ({len(results)} New Model Insights Ingested)!")
    print(f"📄 Appended to {out_file}")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    asyncio.run(run_batch_2())
