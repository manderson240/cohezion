#!/usr/bin/env python3
"""Queries Ollama Cloud Frontier Models for Bleeding-Edge Mathematical & Competition Insights.

Consults:
1. `deepseek-v4-pro:cloud` (1.6T parameter reasoning): Non-Euclidean ARC manifold formulations & discrete geometry.
2. `qwen3.5:397b-cloud` (Frontier code & competitive ML): Pokemon TCG CFR pruning & Biohub cell tracking.
3. `glm-5.2:cloud` (Frontier science & physics): 12-parameter quadrature stability & RSNA Knee multi-view loss.

Outputs compendium to: `docs/research/ollama_cloud_bleeding_edge_advisors_compendium.md`.
"""

import asyncio
import json
import logging
import os
import time
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CLOUD_ADVISOR] %(message)s")
logger = logging.getLogger("cloud_advisor")

OLLAMA_BASE = "http://localhost:11434"

ADVISOR_TASKS = [
    {
        "advisor": "DeepSeek-V4 Pro (1.6T Cloud)",
        "model": "deepseek-v4-pro:cloud",
        "domain": "ARC-AGI ($1.55M) 12D Poincaré Manifolds & Discrete Program Synthesis",
        "prompt": "We have an ARC-AGI solver achieving 25 exact solves across 1,000 official training tasks using a 21-primitive DSL, object-centric CCL area extraction, and Poincaré hyperbolic geodesic pruning. What are 3 bleeding-edge mathematical formulations (e.g. Sheaf Cohomology, Tropical Geometry, Cellular Automata Invariants) that can elevate our program synthesizer to 100+ tasks? Provide concrete formulas and AST implementations."
    },
    {
        "advisor": "Qwen-3.5 397B (Cloud)",
        "model": "qwen3.5:397b-cloud",
        "domain": "Pokemon TCG ($240k) & Biohub Cell Tracking ($60k)",
        "prompt": "Provide bleeding-edge optimizations for: 1) Information-Set MCTS + CFR running 22,700 games/sec (handling imperfect information state abstraction and deck-out stall countermeasures), and 2) Biohub 3D Cell Tracking across mitotic divisions (Kalman-smoothed Hungarian bipartite matching with non-rigid deformation fields). Provide mathematical equations and Python algorithms."
    },
    {
        "advisor": "GLM-5.2 Frontier (Cloud)",
        "model": "glm-5.2:cloud",
        "domain": "12-Parameter Quadrature HIHO Stability & RSNA Knee Detection ($77k)",
        "prompt": "Provide bleeding-edge formulations for: 1) HIHO 0.5 Coherence reality precipitation field mapping for agentic stability, and 2) Multi-view 3D DICOM feature fusion for RSNA Knee abnormality detection (optimizing multi-label area under the curve under severe label imbalance). Provide exact formulas and loss functions."
    }
]

async def query_advisor(client: httpx.AsyncClient, task: dict) -> dict:
    advisor = task["advisor"]
    model = task["model"]
    domain = task["domain"]
    prompt = task["prompt"]

    logger.info("Consulting %s on %s...", advisor, domain)
    t0 = time.perf_counter()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a world-class AI researcher, theoretical physicist, and Kaggle Grandmaster. Provide deep mathematical rigor, equations, and concrete implementation code."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 768
        }
    }

    try:
        r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120.0)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            content = r.json()["message"]["content"].strip()
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            logger.info("✓ %s completed in %.2fs", advisor, dt)
            return {"advisor": advisor, "model": model, "domain": domain, "duration": dt, "response": content, "status": "SUCCESS"}
    except Exception as e:
        logger.warning("Query failed for %s: %s", advisor, e)

    return {"advisor": advisor, "model": model, "domain": domain, "duration": 0.0, "response": "Advisory synthesis unavailable.", "status": "ERROR"}

async def main():
    print("\n" + "=" * 110)
    print("🌐 CONSULTING OLLAMA CLOUD GRAND ADVISORS (DEEPSEEK-1.6T, QWEN-397B, GLM-5.2)")
    print("=" * 110)

    async with httpx.AsyncClient(timeout=150.0) as client:
        results = []
        for task in ADVISOR_TASKS:
            res = await query_advisor(client, task)
            results.append(res)

        os.makedirs("docs/research", exist_ok=True)
        report_file = "docs/research/ollama_cloud_bleeding_edge_advisors_compendium.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 🌐 Ollama Cloud Bleeding-Edge Advisors Compendium\n\n")
            f.write(f"**Date**: 2026-08-24  \n")
            f.write(f"**Advisors Consulted**: DeepSeek-V4 Pro (1.6T), Qwen-3.5 (397B), GLM-5.2 (Frontier Science)  \n\n")

            for r in results:
                print(f"\n[Advisor: {r['advisor']}] ({r['domain']} | {r['duration']}s)")
                print(r["response"][:300] + "...\n" if len(r["response"]) > 300 else r["response"])
                print("-" * 95)

                f.write(f"## {r['advisor']}\n")
                f.write(f"**Domain**: {r['domain']} | **Duration**: {r['duration']}s\n\n")
                f.write(f"{r['response']}\n\n---\n\n")

        print("\n" + "=" * 110)
        print(f"🎉 OLLAMA CLOUD ADVISORY HARVEST COMPLETE! Persisted to: {report_file}")
        print("=" * 110 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
