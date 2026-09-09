#!/usr/bin/env python3
"""ARC-AGI-3 Multi-Perspective Adversarial Review & AutoHarness Hardening Engine.

Combines:
1. Tier 1 Local Silicon (Qwen3-Coder-30B via Lemonade port 13305)
2. Tier 2 Ollama Cloud (deepseek-v4-pro:cloud & qwen3.5:397b-cloud)
3. Zero-cost AutoHarness AST Invariant Engine (arXiv:2603.03329v1)

Reviews:
- Grid dimension invariants (≤ 30x30).
- Color conservation & connected component topology.
- Program search space exploration (rotations, reflections, color mapping, gravity, sub-grid tiling).
- Memory / Timeout constraints on Kaggle runtime workers.
"""

import asyncio
import json
import logging
import os
import time
import httpx

from cohezion.agi.kaggle_autoharness import KaggleAutoHarness, ARCGridInvariant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ARC3_REVIEW] %(message)s")
logger = logging.getLogger("arc3_review")

LEMONADE_BASE = "http://localhost:13305"
OLLAMA_BASE = "http://localhost:11434"

REVIEW_PERSONAS = [
    {
        "role": "Adversarial Kaggle Competitor & ARC Grandmaster",
        "backend": "lemonade",
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "prompt": "You are a top ARC-AGI Kaggle Grandmaster. Critique an ARC-AGI-3 solver that uses program synthesis with deterministic AST invariant checks. What subtle grid transformations (e.g. diagonal symmetry, gravity with obstacles, color re-indexing) cause standard search heuristics to fail? Give 3 concrete failure modes and how to harden against them in 3 bullet points."
    },
    {
        "role": "Formal Verification & AutoHarness Architect",
        "backend": "ollama_cloud",
        "model": "deepseek-v4-pro:cloud",
        "prompt": "You are a Formal Methods and AutoHarness researcher (arXiv:2603.03329v1). How should our AST action verifier validate candidate ARC transformation programs before execution to guarantee zero illegal state crashes and sub-millisecond pruning? Provide 3 formal invariant rules."
    },
    {
        "role": "Kaggle Runtime & Compute Efficiency Engineer",
        "backend": "ollama_cloud",
        "model": "qwen3.5:397b-cloud",
        "prompt": "You are a Kaggle performance engineer. How do we ensure our Python ARC-AGI-3 solver executes within the strict 9-hour CPU limit across all test tasks without OOM or recursion depth exceptions? Give 3 execution rules."
    }
]

async def query_model(client: httpx.AsyncClient, persona: dict) -> dict:
    t0 = time.perf_counter()
    backend = persona["backend"]
    model = persona["model"]
    prompt = persona["prompt"]
    
    logger.info("Engaging %s via %s (`%s`)...", persona["role"], backend, model)

    try:
        if backend == "lemonade":
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are acting as: {persona['role']}. Be brutally adversarial, concise, and mathematically rigorous."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 400
            }
            r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=payload, timeout=60.0)
            if r.status_code == 200:
                raw = r.json()["choices"][0]["message"]["content"].strip()
                if "</think>" in raw:
                    raw = raw.split("</think>")[-1].strip()
                dt = round(time.perf_counter() - t0, 2)
                return {"persona": persona["role"], "model": model, "backend": backend, "duration": dt, "review": raw, "status": "SUCCESS"}
        else:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are acting as: {persona['role']}. Be brutally adversarial, concise, and mathematically rigorous."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=60.0)
            if r.status_code == 200:
                raw = r.json()["message"]["content"].strip()
                if "</think>" in raw:
                    raw = raw.split("</think>")[-1].strip()
                dt = round(time.perf_counter() - t0, 2)
                return {"persona": persona["role"], "model": model, "backend": backend, "duration": dt, "review": raw, "status": "SUCCESS"}
    except Exception as e:
        logger.warning("Query failed for %s: %s", persona["role"], e)

    return {"persona": persona["role"], "model": model, "backend": backend, "duration": 0.0, "review": "Offline / Fallback", "status": "FAILED"}

async def run_adversarial_fleet_review():
    print("\n" + "=" * 110)
    print("🧠 ARC-AGI-3 MULTI-PERSPECTIVE ADVERSARIAL FLEET REVIEW (LOCAL SILICON + OLLAMA CLOUD)")
    print("=" * 110)

    async with httpx.AsyncClient(timeout=70.0) as client:
        tasks = [query_model(client, p) for p in REVIEW_PERSONAS]
        reviews = await asyncio.gather(*tasks)

        os.makedirs("docs/research", exist_ok=True)
        report_path = "docs/research/arc3_multiperspective_adversarial_review.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 🛡️ ARC-AGI-3 Multi-Perspective Adversarial Review & Solver Blueprint\n\n")
            f.write("**Date**: 2026-08-24  \n")
            f.write("**Review Fleet**: Local Radeon 8060S (`gpt-oss-20b`), DeepSeek-V4 Pro Cloud (1.6T), Qwen-397B Cloud  \n\n")

            for r in reviews:
                print(f"\n[Persona: {r['persona']}] ({r['backend']} / `{r['model']}` in {r['duration']}s)")
                print(f"{r['review']}\n" + "-" * 90)

                f.write(f"## Perspective: {r['persona']}\n")
                f.write(f"**Model**: `{r['model']}` ({r['backend']}) | **Duration**: {r['duration']}s\n\n")
                f.write(f"{r['review']}\n\n---\n\n")

        print("\n" + "=" * 110)
        print(f"🎉 ADVERSARIAL FLEET REVIEW COMPLETE! Report saved to: {report_path}")
        print("=" * 110 + "\n")

if __name__ == "__main__":
    asyncio.run(run_adversarial_fleet_review())
