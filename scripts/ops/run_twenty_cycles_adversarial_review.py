#!/usr/bin/env python3
"""Multi-Perspective Adversarial Review of all 20 Autonomous Cycles by Ollama Cloud Models.

Dispatches the complete suite of 20 newly engineered subsystems to 3 frontier cloud personas:
1. `deepseek-v4-pro:cloud` — "Red Team Security, Cryptographic & Distributed Attack Specialist"
2. `qwen3.5:397b-cloud` — "Principal Distributed Systems, UMA Hardware & Concurrency Architect"
3. `glm-5.2:cloud` — "Formal Topological Category Theorist & Mathematical Physicist"
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("adversarial_review_20_cycles")

REVIEWERS = [
    (
        "deepseek-v4-pro:cloud",
        "Red Team Security, Cryptographic & Distributed Attack Specialist",
        "You are an adversarial Red Team Security Specialist. Stress-test the entire 20-cycle suite (ZKFV proofs, DLQ self-healing, fleet concurrency locks, MCP/LangGraph/AutoGen bridges, UMA zero-copy buffers, sandbox gates) for race conditions, replay attacks, memory corruption, and security boundary bypasses.",
    ),
    (
        "qwen3.5:397b-cloud",
        "Principal Distributed Systems, UMA Hardware & Concurrency Architect",
        "You are a Principal Systems Architect specialized in heterogeneous UMA hardware (Strix Halo NPU/iGPU/CPU), cache coherence, asynchronous distributed orchestration, and Markov stream routing. Adversarially critique the 20-cycle deliverables for architectural scalability, thread deadlocks, UMA aliasing hazards, and event-loop bottlenecks.",
    ),
    (
        "glm-5.2:cloud",
        "Formal Topological Category Theorist & Mathematical Physicist",
        "You are a Formal Topological Mathematician and Mathematical Physicist. Adversarially examine the Poincaré 2048D Fréchet centroids, CTAC conformal factors, Sheaf Cohomology Čech nerves, Geodesic Flow Neural ODEs, and 432 Hz HIHO acoustic precipitation for mathematical rigor, dimensional collapse, symplectic volume preservation, and metric singularities.",
    ),
]

CYCLE_FILES = [
    "src/cohezion/physics/ctac_engine.py",
    "src/cohezion/inference/sparse_kv_compactor.py",
    "src/cohezion/agi/zkfv_compiler.py",
    "src/cohezion/physics/geodesic_flow_ode.py",
    "src/cohezion/physics/symmetry_breaker.py",
    "src/cohezion/flume/bioelectric_topology.py",
    "src/cohezion/physics/hiho_streamer.py",
    "src/cohezion/swarm/markov_stream_router.py",
    "src/cohezion/compound/monadic_recovery.py",
    "src/cohezion/data_mesh/graph_relational_mesh.py",
    "src/cohezion/training/dpo_pair_synthesizer.py",
    "src/cohezion/reliability/fleet_concurrency_governor.py",
    "src/cohezion/physics/frechet_centroid.py",
    "src/cohezion/reliability/dlq_self_healer.py",
    "src/cohezion/agi/kaggle_arc_verifier.py",
    "src/cohezion/agi/aimo_step_verifier.py",
    "src/cohezion/adapters/langgraph_async_bridge.py",
    "src/cohezion/adapters/autogen_sheaf_manager.py",
    "src/cohezion/multimodal/uma_buffer_streamer.py",
    "scripts/ops/grand_sovereign_swarm_sweep.py",
]


async def query_model(model_name: str, role: str, persona_prompt: str, code_bundle: str) -> dict:
    logger.info("Dispatching 20-cycle adversarial review to %s (%s)...", model_name, role)
    full_prompt = f"""{persona_prompt}

Perform an exhaustive, adversarial, and uncompromising code review across all 20 newly engineered subsystems of Cohezion.

Source Code Bundle (20 Cycles):
{code_bundle}

Structure your adversarial critique as follows:
1. CRITICAL VULNERABILITIES & SYSTEMIC ARCHITECTURAL RISKS (Categorized by severity).
2. MATHEMATICAL, PHYSICAL, OR HARDWARE-UMA VIOLATIONS.
3. CONCRETE REMEDIATION CODE FIXES & REFACTORING BLUEPRINTS.
4. FORMAL ADVERSARIAL VERDICT: [APPROVED | CHANGES REQUIRED | BLOCKED]
"""
    url = "http://localhost:11434/api/generate"
    data = json.dumps({
        "model": model_name,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.15}
    })
    req = urllib.request.Request(url, data=data.encode("utf-8"), headers={"Content-Type": "application/json"})
    loop = asyncio.get_running_loop()
    try:
        resp_data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=300.0).read().decode("utf-8"))
        res = json.loads(resp_data)
        content = res.get("response") or res.get("thinking") or ""
        return {"model": model_name, "role": role, "content": content, "success": True}
    except Exception as exc:
        logger.error("Model %s review error: %s", model_name, exc)
        return {"model": model_name, "role": role, "content": str(exc), "success": False}


async def main():
    logger.info("=" * 100)
    logger.info("STARTING MULTI-PERSPECTIVE ADVERSARIAL REVIEW OF ALL 20 CYCLES")
    logger.info("=" * 100)

    code_sections = []
    for rel_p in CYCLE_FILES:
        p = REPO_ROOT / rel_p
        if p.exists():
            code_sections.append(f"### Subsystem: `{rel_p}`\n```python\n{p.read_text()}\n```\n")

    full_code_bundle = "\n".join(code_sections)

    tasks = [query_model(m, r, prompt, full_code_bundle) for m, r, prompt in REVIEWERS]
    results = await asyncio.gather(*tasks)

    report_lines = [
        "# Multi-Perspective Adversarial Review: All 20 Autonomous Cycles\n",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n",
        "**Evaluators**: `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`\n\n---\n",
    ]

    for r in results:
        report_lines.append(f"## Perspective: {r['model']} — {r['role']}\n\n")
        report_lines.append(r["content"].strip())
        report_lines.append("\n\n---\n")

    report_file = REPO_ROOT / "docs/research/twenty_cycles_adversarial_review.md"
    report_file.write_text("\n".join(report_lines))
    logger.info("✅ Saved 20-cycle multiperspective adversarial review to %s", report_file)


if __name__ == "__main__":
    asyncio.run(main())
