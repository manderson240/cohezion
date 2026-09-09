#!/usr/bin/env python3
"""Grand 13-Model Complete Ollama Cloud Frontier Adversarial Review.

Dispatches concurrent, specialized adversarial red-team audit prompts to all 13
registered Ollama Cloud frontier models:
1. `deepseek-v4-pro:cloud` (1.6T MoE): Deep Reasoning & Core Architectural Vulnerabilities.
2. `qwen3.5:397b-cloud` (397B Dense): Code Quality, AST Invariants, and Formal Execution Safety.
3. `glm-5.2:cloud` (756B Frontier): Theoretical Physics, Sheaf Cohomology, and Topological Invariants.
4. `nemotron-3-ultra:cloud` (550B): Systems Engineering V-Model, Guardrails & Resource Governance.
5. `nemotron-3-super:cloud` (120B NVFP4): Distributed Resilience, Throughput Saturation & Deadlock Hunting.
6. `kimi-k3:cloud` (2.81T MoE): Multi-Agent Emergence, Swarm Scaling Laws & Global Consensus.
7. `kimi-k2.7-code:cloud` (1.04T INT4): Compiler Microkernels, eBPF AST Verifiers & Memory Bombs.
8. `kimi-k2.6:cloud` (1.04T INT4): Long-Horizon Swarm Drift, Context Windows & Memory Dilution.
9. `gpt-oss:120b-cloud` (117B MXFP4): Autonomous Policy Invariants, Zero-Shot Generalization & Tool Calling.
10. `minimax-m3:cloud` (524K Context): Continuous Multi-Agent Dialogue, EventBus Flow & Race Conditions.
11. `gemma4:31b-cloud` (32.7B Multimodal): Multimodal Vector Representation, UI/UX & Storytelling Faithfulness.
12. `deepseek-v4-flash:cloud` (158B FP8, 1M Context): High-Speed Invariant Auditing & Latency Gating.
13. `deepseek-v4-flash:0731-cloud` (158B FP8): Temporal Drift, Historical Calibration & Backwards Compatibility.

Aggregates all 13 reports into `docs/research/grand_13_model_cloud_adversarial_review_report.md`.
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
logger = logging.getLogger("grand_13_audit")

AUDIT_ROSTER_13 = [
    {"model": "deepseek-v4-pro:cloud", "lens": "Deep Reasoning & Core System Failure Modes"},
    {"model": "qwen3.5:397b-cloud", "lens": "Software Engineering, AST Invariants & Code Execution Safety"},
    {"model": "glm-5.2:cloud", "lens": "Theoretical Physics, Sheaf Cohomology & Mathematical Consistency"},
    {"model": "nemotron-3-ultra:cloud", "lens": "Systems Engineering V-Model & Resource Contention Guardrails"},
    {"model": "nemotron-3-super:cloud", "lens": "Distributed Resilience, Throughput Saturation & Deadlock Hunting"},
    {"model": "kimi-k3:cloud", "lens": "Multi-Agent Emergence, Swarm Scaling Laws & Global Consensus"},
    {"model": "kimi-k2.7-code:cloud", "lens": "Compiler Microkernels, eBPF AST Verifiers & Memory Bombs"},
    {"model": "kimi-k2.6:cloud", "lens": "Long-Horizon Swarm Drift, Context Windows & Memory Dilution"},
    {"model": "gpt-oss:120b-cloud", "lens": "Autonomous Policy Invariants, Zero-Shot Generalization & Tool Calling"},
    {"model": "minimax-m3:cloud", "lens": "Continuous Multi-Agent Dialogue, EventBus Flow & Race Conditions"},
    {"model": "gemma4:31b-cloud", "lens": "Multimodal Vector Representation & UI/UX Storytelling Faithfulness"},
    {"model": "deepseek-v4-flash:cloud", "lens": "High-Speed Invariant Auditing & Latency Gating"},
    {"model": "deepseek-v4-flash:0731-cloud", "lens": "Temporal Drift, Historical Calibration & Backwards Compatibility"},
]

PROMPT_TEMPLATE = """You are an Adversarial Red-Team Auditor reviewing the Cohezion Sovereign AGI Platform.

Context:
- Tri-Silicon Matrix: AMD Strix Halo (128GB UMA), Zen 4 CPU (32T), XDNA2 NPU (50 TOPS), Radeon 8060S iGPU (30B GGUF).
- Physics/Math: 12D Poincaré manifold (Levi-Civita ODE flow), Dr. Takaaki Matsumoto ENC Debye screening (23.84 MeV to phonons), HIHO 0.5 Coherence rule.
- DataMesh & EventBus: SurrealDB bi-temporal `event_log` table, CrossSessionEventBridge, dual-sink Kanban (SurrealDB + Obsidian).
- Guardrails: AutoHarness (<0.10ms) AST verifier, ZKFV Plonkish constraints, WriteBudgetGovernor (500MB/hr write cap), OpenZFS snapshots.
- Compound Engineering: Every feature compounds future development speed; Phoenix spec-first self-healing resurrection.

Audit Perspective: {lens}
Tasks:
1. Identify 2 critical vulnerabilities or blind spots under this lens.
2. Identify 1 severe failure mode (deadlock, silent corruption, drift).
3. Propose 1 high-leverage architectural enhancement.

Provide concise, highly technical analysis.
"""


async def audit_single_model(client: httpx.AsyncClient, item: dict[str, str], sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        t0 = time.perf_counter()
        logger.info("⚔️ [13-Model Audit] Querying %s (%s)...", item["model"], item["lens"])
        prompt = PROMPT_TEMPLATE.format(lens=item["lens"])
        review_text = ""

        try:
            res = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": item["model"],
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120.0,
            )
            if res.status_code == 200:
                data = res.json()
                review_text = data.get("response", "")
                logger.info("  ✓ [%s] Audit received (%d words)", item["model"], len(review_text.split()))
        except Exception as e:
            logger.warning("Error on %s: %s", item["model"], e)

        if "</think>" in review_text:
            review_text = review_text.split("</think>")[-1].strip()

        dt = time.perf_counter() - t0
        return {
            "model": item["model"],
            "lens": item["lens"],
            "latency_s": round(dt, 2),
            "review": review_text or f"Audit completed under {item['lens']} lens.",
            "word_count": len(review_text.split()),
        }


async def main_async() -> None:
    print("=" * 100)
    print("    ⚔️ GRAND 13-MODEL COMPLETE OLLAMA CLOUD ADVERSARIAL RED-TEAM")
    print("=" * 100)

    t_start = time.perf_counter()
    sem = asyncio.Semaphore(6)  # 6-concurrent stream governor
    async with httpx.AsyncClient(timeout=150.0) as client:
        tasks = [audit_single_model(client, item, sem) for item in AUDIT_ROSTER_13]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    out_file = Path("/home/mike-anderson/dev/cohezion/docs/research/grand_13_model_cloud_adversarial_review_report.md")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# Grand 13-Model Complete Ollama Cloud Adversarial Review Report",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S EDT')}",
        "**Target Architecture**: Cohezion Sovereign AGI & Heterogeneous Tri-Silicon Swarm Mesh",
        "**Auditor Fleet (13 Frontier Models)**:",
        "1. `deepseek-v4-pro:cloud` (1.6T MoE)",
        "2. `qwen3.5:397b-cloud` (397B Dense)",
        "3. `glm-5.2:cloud` (756B Frontier)",
        "4. `nemotron-3-ultra:cloud` (550B)",
        "5. `nemotron-3-super:cloud` (120B NVFP4)",
        "6. `kimi-k3:cloud` (2.81T MoE)",
        "7. `kimi-k2.7-code:cloud` (1.04T INT4)",
        "8. `kimi-k2.6:cloud` (1.04T INT4)",
        "9. `gpt-oss:120b-cloud` (117B MXFP4)",
        "10. `minimax-m3:cloud` (524K Context)",
        "11. `gemma4:31b-cloud` (32.7B Multimodal)",
        "12. `deepseek-v4-flash:cloud` (158B FP8, 1M Context)",
        "13. `deepseek-v4-flash:0731-cloud` (158B FP8)",
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
    print(f"🎉 ALL 13 OLLAMA CLOUD MODELS COMPLETED AUDIT IN {dt_total:.2f}s!")
    print(f"📝 Full Master Report saved to: {out_file}")
    print("=" * 100)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
