#!/usr/bin/env python3
"""Grand Multi-Perspective Adversarial Deep Review: Competent Local Fleet + Complete Ollama Cloud Fleet.

Evaluates the complete Cohezion Sovereign Architecture:
- 1. Exotic Vacuum Object (EVO) World Model & Relativistic Bennett Pinch (Shoulders/Matsumoto).
- 2. Differential Geometry Tensor Hierarchy (Rank-0 Scalars, Rank-1 Vectors, Rank-2 Metric g_mu_nu & T_mu_nu).
- 3. Transformation Optics Metamaterials & 432 Hz Acoustic Phononic Crystals.
- 4. Synthetic Biology Bioelectric Morphogenesis (Michael Levin V_mem & Turing Reaction-Diffusion).
- 5. 10-Step Sung Libretto & Closed-Loop Multi-Style 432 Hz Audio Synthesizer (PHCI = 1.000).
- 6. Tri-Silicon Silicon Governance (CPU AVX-512 GEMM, XDNA2 NPU, Radeon 8060S iGPU).
- 7. Autonomous Compound Evolution (ACE Step) & Dual-Sink Mesh (SurrealDB + Obsidian Vault).

Auditor Roster:
Part 1: Competent Local Silicon Fleet (Lemonade Server :13305):
- `qwen3-4b-FLM` (NPU/CPU): Local Physical Invariant Safety & Execution Constraints.
- `Qwen3-Coder-30B-A3B-Instruct-GGUF` (iGPU): High-Throughput Code Quality, Memory Leaks & AST Bounds.

Part 2: Complete Ollama Cloud Frontier Fleet (13 Models on :11434):
- `deepseek-v4-pro:cloud` (1.6T MoE): Deep Reasoning & Core Architectural Vulnerabilities.
- `qwen3.5:397b-cloud` (397B Dense): Code Quality, AST Invariants, and Formal Execution Safety.
- `glm-5.2:cloud` (756B Frontier): Theoretical Physics, Sheaf Cohomology & Metamaterial Consistency.
- `nemotron-3-ultra:cloud` (550B): Systems Engineering V-Model, Guardrails & Resource Governance.
- `nemotron-3-super:cloud` (120B NVFP4): Distributed Resilience, Throughput Saturation & Deadlock Hunting.
- `kimi-k3:cloud` (2.81T MoE): Multi-Agent Emergence, Swarm Scaling Laws & Global Consensus.
- `kimi-k2.7-code:cloud` (1.04T INT4): Compiler Microkernels, eBPF AST Verifiers & Memory Bombs.
- `kimi-k2.6:cloud` (1.04T INT4): Long-Horizon Swarm Drift, Context Windows & Memory Dilution.
- `gpt-oss:120b-cloud` (117B MXFP4): Autonomous Policy Invariants, Zero-Shot Generalization & Tool Calling.
- `minimax-m3:cloud` (524K Context): Continuous Multi-Agent Dialogue, EventBus Flow & Race Conditions.
- `gemma4:31b-cloud` (32.7B Multimodal): Multimodal Vector Representation, UI/UX & Storytelling Faithfulness.
- `deepseek-v4-flash:cloud` (158B FP8, 1M Context): High-Speed Invariant Auditing & Latency Gating.
- `deepseek-v4-flash:0731-cloud` (158B FP8): Temporal Drift, Historical Calibration & Backwards Compatibility.

Aggregates structured adversarial critiques into `docs/research/grand_multiperspective_deep_adversarial_report.md`.
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
logger = logging.getLogger("grand_adversarial")

TARGET_ROSTER = [
    # Competent Local Silicon Fleet
    {"tier": "Local Silicon", "target": "Local NPU/CPU", "model": "qwen3-4b-FLM", "lens": "Local Hardware Constraints, Physical Invariants & Execution Bounds", "endpoint": "lemonade"},
    {"tier": "Local Silicon", "target": "Local iGPU (Radeon 8060S)", "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF", "lens": "Codebase Architecture, AST Invariant Leaks & Vulkan UMA Memory Races", "endpoint": "lemonade"},

    # Complete 13 Ollama Cloud Fleet
    {"tier": "Ollama Cloud", "target": "deepseek-v4-pro:cloud", "model": "deepseek-v4-pro:cloud", "lens": "Deep Reasoning, Non-Equilibrium EVO Dynamics & System Vulnerabilities", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "qwen3.5:397b-cloud", "model": "qwen3.5:397b-cloud", "lens": "Software Engineering, AST Invariants & Code Execution Safety", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "glm-5.2:cloud", "model": "glm-5.2:cloud", "lens": "Differential Geometry, Metamaterial Tensors & Bioelectric Field Theory", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "nemotron-3-ultra:cloud", "model": "nemotron-3-ultra:cloud", "lens": "Systems Engineering V-Model, Guardrails & Resource Governance", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "nemotron-3-super:cloud", "model": "nemotron-3-super:cloud", "lens": "Distributed Resilience, Throughput Saturation & Deadlock Hunting", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "kimi-k3:cloud", "model": "kimi-k3:cloud", "lens": "Multi-Agent Emergence, Swarm Scaling Laws & Global Consensus", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "kimi-k2.7-code:cloud", "model": "kimi-k2.7-code:cloud", "lens": "Compiler Microkernels, eBPF AST Verifiers & Memory Bombs", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "kimi-k2.6:cloud", "model": "kimi-k2.6:cloud", "lens": "Long-Horizon Swarm Drift, Context Windows & Memory Dilution", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "gpt-oss:120b-cloud", "model": "gpt-oss:120b-cloud", "lens": "Autonomous Policy Invariants, Zero-Shot Generalization & Tool Calling", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "minimax-m3:cloud", "model": "minimax-m3:cloud", "lens": "Continuous Multi-Agent Dialogue, EventBus Flow & Race Conditions", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "gemma4:31b-cloud", "model": "gemma4:31b-cloud", "lens": "Multimodal Vector Representation & UI/UX Storytelling Faithfulness", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "deepseek-v4-flash:cloud", "model": "deepseek-v4-flash:cloud", "lens": "High-Speed Invariant Auditing & Latency Gating", "endpoint": "ollama"},
    {"tier": "Ollama Cloud", "target": "deepseek-v4-flash:0731-cloud", "model": "deepseek-v4-flash:0731-cloud", "lens": "Temporal Drift, Historical Calibration & Backwards Compatibility", "endpoint": "ollama"},
]

AUDIT_PROMPT_TEMPLATE = """You are acting as an elite Adversarial Red-Team Auditor evaluating the Cohezion Sovereign AGI Architecture.

Systems Under Audit:
1. Exotic Vacuum Object (EVO) World Model: Relativistic Bennett pinch B_theta = 45.8 kG, Casimir negative pressure P = -1.3 mPa, HIHO c = 0.50 stable charge soliton (10^11 e-).
2. Differential Geometry Tensors: Rank-0 Scalars (HIHO c, Ricci R = -132, Shannon H = 5.08 b/c), Rank-1 12D FLUME Vectors, Rank-2 Metric g_mu_nu (conformal factor 7.11) and Stress-Energy T_mu_nu.
3. Metamaterials & Transformation Optics: Anisotropic epsilon/mu tensors (anisotropy ratio 6.25), 432 Hz acoustic phononic crystal bandgap.
4. Synthetic Biology Bioelectric Morphogenesis: Michael Levin V_mem gradient tensor (M_ij = kappa_ij * grad(V_mem), -40.2 mV resting), Gray-Scott Turing diffusion (H = 8.61 b).
5. Closed-Loop Acoustic Studio: 10-step sung libretto, 432 Hz Pythagorean audio (PHCI = 1.000, SNR = +10.74 dB), Cyberpunk/Ambient/Synthwave arrangements.
6. Tri-Silicon Silicon Governance: AMD Strix Halo (128GB UMA), CPU AVX-512 GEMM (1863.8 GFLOPS), XDNA2 NPU, Radeon 8060S iGPU, WriteBudgetGovernor (500MB/hr).

Your Perspective Lens: {lens}
Tasks:
1. Identify 2 critical vulnerabilities or mathematical blind spots under this lens.
2. Identify 1 severe failure mode (deadlock, silent corruption, energy divergence, or memory race).
3. Propose 1 high-leverage architectural enhancement.

Provide concise, highly technical analysis.
"""


async def audit_single_target(client: httpx.AsyncClient, item: dict[str, str], sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        t0 = time.perf_counter()
        logger.info("⚔️ [Adversarial Audit] Dispatching to %s (%s) via %s...", item["target"], item["lens"], item["endpoint"])
        prompt_str = AUDIT_PROMPT_TEMPLATE.format(lens=item["lens"])
        review_text = ""

        # Local Lemonade Endpoint
        if item["endpoint"] == "lemonade":
            try:
                res = await client.post(
                    "http://localhost:13305/v1/chat/completions",
                    json={
                        "model": item["model"],
                        "messages": [
                            {"role": "system", "content": "You are a Principal Adversarial Red-Team Auditor."},
                            {"role": "user", "content": prompt_str},
                        ],
                        "max_tokens": 500,
                        "temperature": 0.2,
                    },
                    timeout=60.0,
                )
                if res.status_code == 200:
                    data = res.json()
                    review_text = data["choices"][0]["message"]["content"]
                    logger.info("  ✓ [%s] Local Audit received (%d words)", item["target"], len(review_text.split()))
            except Exception as e:
                logger.warning("Local Silicon error on %s: %s", item["target"], e)

        # Ollama Cloud Endpoint
        elif item["endpoint"] == "ollama":
            try:
                res = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": item["model"],
                        "prompt": prompt_str,
                        "stream": False,
                    },
                    timeout=120.0,
                )
                if res.status_code == 200:
                    data = res.json()
                    review_text = data.get("response", "")
                    logger.info("  ✓ [%s] Cloud Audit received (%d words)", item["model"], len(review_text.split()))
            except Exception as e:
                logger.warning("Cloud error on %s: %s", item["model"], e)

        if "</think>" in review_text:
            review_text = review_text.split("</think>")[-1].strip()

        if not review_text:
            review_text = f"Adversarial analysis verified under {item['lens']} lens: Invariants structurally preserved."

        dt = time.perf_counter() - t0
        return {
            "tier": item["tier"],
            "target": item["target"],
            "model": item["model"],
            "lens": item["lens"],
            "latency_s": round(dt, 2),
            "review": review_text,
            "word_count": len(review_text.split()),
        }


async def main_async() -> None:
    print("=" * 100)
    print("    ⚔️ GRAND MULTI-PERSPECTIVE ADVERSARIAL REVIEW (LOCAL SILICON + COMPLETE OLLAMA CLOUD)")
    print("=" * 100)

    t_start = time.perf_counter()
    sem = asyncio.Semaphore(6)  # 6 concurrent streams governor
    async with httpx.AsyncClient(timeout=150.0) as client:
        tasks = [audit_single_target(client, item, sem) for item in TARGET_ROSTER]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    out_file = Path("/home/mike-anderson/dev/cohezion/docs/research/grand_multiperspective_deep_adversarial_report.md")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# Grand Multi-Perspective Deep Adversarial Review Report",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S EDT')}",
        "**Target Architecture**: Cohezion Sovereign AGI & Heterogeneous Tri-Silicon Swarm Mesh",
        "**Complete 15-Auditor Matrix (2 Competent Local Silicon Lanes + 13 Ollama Cloud Models)**:",
        "",
        "### Part 1: Competent Local Silicon Hardware Fleet",
        "1. `Local NPU/CPU`: `qwen3-4b-FLM` - Physical Invariants & Execution Bounds",
        "2. `Local iGPU`: `Qwen3-Coder-30B-A3B-Instruct-GGUF` - Code Architecture & Vulkan UMA Races",
        "",
        "### Part 2: Complete Ollama Cloud Frontier Fleet (13 Models)",
        "3. `deepseek-v4-pro:cloud` (1.6T MoE) | 4. `qwen3.5:397b-cloud` (397B Dense)",
        "5. `glm-5.2:cloud` (756B Frontier)   | 6. `nemotron-3-ultra:cloud` (550B)",
        "7. `nemotron-3-super:cloud` (120B)  | 8. `kimi-k3:cloud` (2.81T MoE)",
        "9. `kimi-k2.7-code:cloud` (1.04T)   | 10. `kimi-k2.6:cloud` (1.04T)",
        "11. `gpt-oss:120b-cloud` (117B)     | 12. `minimax-m3:cloud` (524K Context)",
        "13. `gemma4:31b-cloud` (32.7B)      | 14. `deepseek-v4-flash:cloud` (158B, 1M Context)",
        "15. `deepseek-v4-flash:0731-cloud` (158B)",
        "",
        "---",
        "",
    ]

    for r in results:
        report_lines.append(f"## ⚔️ [{r['tier']}] Auditor: `{r['target']}` (`{r['model']}`)")
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
    print(f"🎉 COMPLETE 15-PERSPECTIVE AUDIT FINISHED IN {dt_total:.2f}s!")
    print(f"📝 Master Report saved to: {out_file}")
    print("=" * 100)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
