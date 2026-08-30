#!/usr/bin/env python3
"""Queries Ollama Cloud Thinking Models for Bleeding-Edge Mathematical Formulations.

Properly extracts `message.content` from Ollama's thinking models (DeepSeek-V4 Pro, Qwen-397B, GLM-5.2).
"""

import asyncio
import json
import logging
import os
import time
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CLOUD_THINKING] %(message)s")
logger = logging.getLogger("cloud_thinking")

OLLAMA_BASE = "http://localhost:11434"

PROMPTS = [
    {
        "title": "DeepSeek-V4 Pro (1.6T Cloud): Sheaf Theory & Hyperbolic ARC Invariants",
        "model": "deepseek-v4-pro:cloud",
        "prompt": "Provide 3 bleeding-edge mathematical formulations for ARC-AGI program synthesis using: 1) Sheaf Cohomology restriction maps across local grid neighborhoods, 2) Poincaré Hyperbolic Geodesic pruning $d_P(u,v)$, and 3) Minimum Description Length (MDL) Bayesian search trees. Include exact LaTeX equations and concrete algorithmic steps."
    },
    {
        "title": "Qwen-3.5 397B (Cloud): Imperfect Information MCTS & Hungarian Deformable Matching",
        "model": "qwen3.5:397b-cloud",
        "prompt": "Provide bleeding-edge formulations for: 1) Information-Set MCTS with Counterfactual Regret Minimization (CFR) regret-matching bounds for competitive TCGs, and 2) Kalman-smoothed Hungarian bipartite matching with non-rigid thin-plate splines for Biohub 3D cell tracking. Include exact equations and algorithmic complexity."
    },
    {
        "title": "GLM-5.2 (Cloud): Multi-View 3D DICOM Focal Loss & HIHO 0.5 Coherence",
        "model": "glm-5.2:cloud",
        "prompt": "Provide bleeding-edge formulations for: 1) Multi-view 3D DICOM feature fusion using asymmetric focal loss $FL(p_t) = -\alpha_t (1-p_t)^\gamma \log(p_t)$ for RSNA Knee abnormality detection, and 2) 12-parameter quadrature field stability around the 0.5 HIHO coherence point. Include exact formulas and loss gradients."
    }
]

async def query_cloud_model(client: httpx.AsyncClient, item: dict) -> dict:
    title = item["title"]
    model = item["model"]
    prompt = item["prompt"]

    logger.info("Querying %s...", title)
    t0 = time.perf_counter()

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2}
    }

    try:
        r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120.0)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            data = r.json()
            msg = data.get("message", {})
            content = msg.get("content", "").strip()
            thinking = msg.get("thinking", "").strip()
            logger.info("✓ %s completed in %.2fs (Content: %d chars, Thinking: %d chars)", title, dt, len(content), len(thinking))
            return {"title": title, "model": model, "duration": dt, "content": content, "status": "SUCCESS"}
    except Exception as e:
        logger.warning("Query failed for %s: %s", title, e)

    return {"title": title, "model": model, "duration": 0.0, "content": "Advisory unavailable.", "status": "ERROR"}

async def main():
    print("\n" + "=" * 110)
    print("🌐 CONSULTING OLLAMA CLOUD THINKING FLEET (DEEPSEEK-1.6T, QWEN-397B, GLM-5.2)")
    print("=" * 110)

    async with httpx.AsyncClient(timeout=900.0) as client:
        results = []
        for p in PROMPTS:
            res = await query_cloud_model(client, p)
            results.append(res)

        os.makedirs("docs/research", exist_ok=True)
        report_file = "docs/research/ollama_cloud_bleeding_edge_advisors_compendium.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 🌐 Ollama Cloud Bleeding-Edge Advisors Compendium\n\n")
            f.write(f"**Date**: 2026-08-24  \n")
            f.write(f"**Frontier Models**: DeepSeek-V4 Pro (1.6T), Qwen-3.5 (397B), GLM-5.2 (Frontier Science)  \n\n")

            for r in results:
                print(f"\n[{r['title']}] ({r['duration']}s)")
                print(r["content"][:400] + "...\n" if len(r["content"]) > 400 else r["content"])
                print("-" * 95)

                f.write(f"## {r['title']}\n")
                f.write(f"**Duration**: {r['duration']}s\n\n")
                f.write(f"{r['content']}\n\n---\n\n")

        print("\n" + "=" * 110)
        print(f"🎉 OLLAMA CLOUD ADVISORY HARVEST COMPLETE! Saved to: {report_file}")
        print("=" * 110 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
