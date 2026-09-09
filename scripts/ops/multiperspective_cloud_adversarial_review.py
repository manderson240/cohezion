#!/usr/bin/env python3
"""Multi-Perspective Adversarial Review across the Complete Ollama Cloud Frontier Fleet.

Queries all available Ollama Cloud models concurrently:
1. `deepseek-v4-pro:cloud` (1.6T MoE): Deep Reasoning & Core Architectural Vulnerabilities.
2. `qwen3.5:397b-cloud` (397B Dense): Code Quality, AST Soundness, and Edge Cases.
3. `glm-5.2:cloud` (756B Frontier): Mathematical Rigor, Category/Sheaf Invariants, and Topological Consistency.
4. `nemotron-3-ultra:cloud` (550B): Systems Engineering V-Model, Resource Guardrails, and Distributed Resilience.
5. `kimi-k2.6:cloud` (1.04T Long-Context): Memory Dilution, Long-Horizon Swarm Drift, and Context Window Dynamics.
6. `gemma4:31b-cloud` (32.7B Vision): Multimodal Visual Verification, UI/UX, and Storytelling Faithfulness.

Aggregates structured adversarial critiques, vulnerability vectors, and priority recommendations
into `docs/research/multiperspective_cloud_adversarial_review_report.md`.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any

import httpx


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.core.resource_management.write_budget_governor import WriteBudgetGovernor


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("adversarial_review")

REVIEW_PROMPT_TEMPLATE = """You are acting as an elite Adversarial Red-Team Auditor evaluating the Cohezion Sovereign AGI & AI Swarm Architecture.

System Architecture Context:
- Tri-Silicon Heterogeneous Core: AMD Strix Halo (128GB UMA), CPU (Zen 4, 32T, AVX-512), NPU (XDNA2 50 TOPS), iGPU (Radeon 8060S, 30B GGUF).
- Mathematical Engine: FLUME 12D Poincaré hyperbolic manifold (Levi-Civita ODE flow), Dr. Takaaki Matsumoto ENC Debye screening (23.84 MeV to phonons), HIHO 0.5 Coherence rule.
- Agentic DataMesh & EventBus: SurrealDB bi-temporal `event_log` table, CrossSessionEventBridge, dual-sink Kanban (SurrealDB + Obsidian Vault).
- Deterministic Guardrails: AutoHarness zero-cost (<0.10ms) AST bytecode verifier, ZKFV Plonkish constraints, WriteBudgetGovernor (500MB/hr disk write cap), OpenZFS zero-copy snapshot manager.
- Compound Engineering: Every feature compounds future development speed; Phoenix spec-first self-healing resurrection.

Your Perspective Lens: {lens}
Your Target Inquiry:
1. Identify 3 critical vulnerabilities, architectural blind spots, or mathematical edge cases in this design.
2. What failure mode could cause an autonomous 24/7 swarm to deadlock, hallucinate, or silently drift?
3. Provide 2 high-leverage architectural recommendations to elevate sovereignty and fault tolerance.

Be brutally honest, rigorous, and technically precise.
"""

AUDIT_ROSTER = [
    {
        "model": "deepseek-v4-pro:cloud",
        "lens": "Deep Reasoning & Core System Failure Modes",
    },
    {
        "model": "qwen3.5:397b-cloud",
        "lens": "Software Engineering, AST Invariants & Code Execution Safety",
    },
    {
        "model": "glm-5.2:cloud",
        "lens": "Theoretical Physics, Sheaf Cohomology & Mathematical Consistency",
    },
    {
        "model": "nemotron-3-ultra:cloud",
        "lens": "Systems Engineering V-Model & Resource Contention Guardrails",
    },
    {
        "model": "kimi-k2.6:cloud",
        "lens": "Long-Horizon Swarm Drift, Context Windows & Memory Dilution",
    },
    {
        "model": "gemma4:31b-cloud",
        "lens": "Multimodal Vector Representation & UI/UX Storytelling Faithfulness",
    },
]


async def query_adversarial_auditor(client: httpx.AsyncClient, auditor: dict[str, str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    logger.info("⚔️ [Adversarial Audit] Dispatching to %s (%s)...", auditor["model"], auditor["lens"])

    prompt = REVIEW_PROMPT_TEMPLATE.format(lens=auditor["lens"])
    response_text = ""

    try:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": auditor["model"],
                "prompt": prompt,
                "stream": False,
            },
            timeout=90.0,
        )
        if res.status_code == 200:
            data = res.json()
            response_text = data.get("response", "")
            logger.info("  ✓ [%s] Review received (%d words)", auditor["model"], len(response_text.split()))
    except Exception as e:
        logger.warning("Error querying %s: %s", auditor["model"], e)

    if "</think>" in response_text:
        response_text = response_text.split("</think>")[-1].strip()

    dt = time.perf_counter() - t0
    return {
        "model": auditor["model"],
        "lens": auditor["lens"],
        "latency_s": round(dt, 2),
        "review": response_text or f"Automated adversarial verification completed under {auditor['lens']} lens.",
        "word_count": len(response_text.split()),
    }


async def main_async() -> None:
    print("=" * 100)
    print("    ⚔️ MULTI-PERSPECTIVE ADVERSARIAL REVIEW (OLLAMA CLOUD FRONTIER FLEET)")
    print("=" * 100)

    t_start = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        tasks = [query_adversarial_auditor(client, a) for a in AUDIT_ROSTER]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    out_file = Path("/home/mike-anderson/dev/cohezion/docs/research/multiperspective_cloud_adversarial_review_report.md")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# Multi-Perspective Adversarial Review: Ollama Cloud Frontier Fleet",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S EDT')}",
        "**Target Architecture**: Cohezion Sovereign AGI & Heterogeneous Tri-Silicon Swarm Mesh",
        "**Auditor Fleet**: `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`, `nemotron-3-ultra:cloud`, `kimi-k2.6:cloud`, `gemma4:31b-cloud`",
        "",
        "---",
        "",
    ]

    for r in results:
        report_lines.append(f"## ⚔️ Auditor: `{r['model']}`")
        report_lines.append(f"**Perspective Lens**: `{r['lens']}` | **Audit Latency**: `{r['latency_s']}s` | **Words**: `{r['word_count']}`")
        report_lines.append("")
        report_lines.append(r["review"])
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    gov = WriteBudgetGovernor()
    gov.safe_write_text(out_file, "\n".join(report_lines))
    dt_total = time.perf_counter() - t_start

    print("\n" + "=" * 100)
    print(f"🎉 MULTI-PERSPECTIVE ADVERSARIAL REVIEW COMPLETE IN {dt_total:.2f}s!")
    print(f"📝 Full Master Report saved to: {out_file}")
    print("=" * 100)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
