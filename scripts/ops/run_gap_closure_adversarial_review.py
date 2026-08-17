#!/usr/bin/env python3
"""Multi-Perspective Adversarial Review of Cohezion's Completed 4-Phase Gap-Closure Deliverables.

Dispatches complete source diffs of:
1. `src/cohezion/mcp/cohezion_agi_server.py` (Premier MCP Server)
2. `src/cohezion/adapters/interop.py` (LangGraph & AutoGen Interop Adapters)
3. `src/cohezion/flume/observability_hud.py` (Real-Time Observability HUD)
4. `src/cohezion/security/micro_sandbox.py` (Micro-Sandbox & Sanitization Engine)
5. `scripts/ops/verify_gap_closure_suite.py` (Certification Harness)

To 3 distinct frontier personas in Ollama Cloud:
- Persona 1 (`deepseek-v4-pro:cloud`): "Red Team Security & Cryptographic Attack Specialist"
- Persona 2 (`qwen3.5:397b-cloud`): "Principal Distributed Systems & Interoperability Architect"
- Persona 3 (`glm-5.2:cloud`): "Topological Mathematics & Sheaf Cohomology Formal Theorist"
"""

import asyncio
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gap_closure_adversarial_review")

REVIEWERS = [
    (
        "deepseek-v4-pro:cloud",
        "Red Team Security, Cryptographic & Sandbox Attack Specialist",
        "You are an adversarial Red Team Security Researcher. Stress-test the new `micro_sandbox.py`, `cohezion_agi_server.py`, and `DataProvenanceSigner` for escape vulnerabilities, prompt injection bypasses, subprocess timeouts, and token replay attacks.",
    ),
    (
        "qwen3.5:397b-cloud",
        "Principal Distributed Systems & Interoperability Architect",
        "You are a Principal Distributed Systems Engineer specialized in MCP, LangGraph, and AutoGen. Adversarially critique `adapters/interop.py` and `cohezion_agi_server.py` for concurrency bottlenecks, schema mismatches, type strictness, and ecosystem compatibility.",
    ),
    (
        "glm-5.2:cloud",
        "Topological Mathematics & Sheaf Cohomology Formal Theorist",
        "You are a Formal Topological Mathematician. Adversarially examine the Poincaré hyperbolic calculations in `poincare_manifold.py`, the Čech cohomology checks in `sheaf_consistency_gate.py`, and the HIHO sonification metrics in `observability_hud.py` for mathematical edge cases, dimensional mismatch, or metric boundary violations.",
    ),
]

FILES_TO_REVIEW = [
    "src/cohezion/mcp/cohezion_agi_server.py",
    "src/cohezion/adapters/interop.py",
    "src/cohezion/flume/observability_hud.py",
    "src/cohezion/security/micro_sandbox.py",
    "scripts/ops/verify_gap_closure_suite.py",
]


async def query_model(model_name: str, role: str, persona_prompt: str, code_bundle: str) -> dict:
    logger.info("Dispatching review to %s (%s)...", model_name, role)
    full_prompt = f"""{persona_prompt}

Perform a rigorous, adversarial, and uncompromising code review of the newly implemented Cohezion Gap-Closure Deliverables.

Source Files Bundle:
{code_bundle}

Provide your adversarial review with:
1. CRITICAL VULNERABILITIES / ARCHITECTURAL FLAWS (Foundations, race conditions, edge cases).
2. EDGE-CASE ATTACK VECTORS OR MATHEMATICAL VIOLATIONS.
3. CONCRETE HARDENING RECOMMENDATIONS (With exact code fixes where applicable).
4. FINAL VERDICT: [APPROVED | CHANGES REQUIRED | BLOCKED]
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
        resp_data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=180.0).read().decode("utf-8"))
        res = json.loads(resp_data)
        content = res.get("response") or res.get("thinking") or ""
        return {"model": model_name, "role": role, "content": content, "success": True}
    except Exception as exc:
        logger.error("Model %s error: %s", model_name, exc)
        return {"model": model_name, "role": role, "content": str(exc), "success": False}


async def main():
    logger.info("=" * 90)
    logger.info("STARTING MULTI-PERSPECTIVE ADVERSARIAL REVIEW OF GAP-CLOSURE SUITE")
    logger.info("=" * 90)

    code_sections = []
    for rel_p in FILES_TO_REVIEW:
        p = REPO_ROOT / rel_p
        if p.exists():
            code_sections.append(f"### File: `{rel_p}`\n```python\n{p.read_text()}\n```\n")

    full_code_bundle = "\n".join(code_sections)

    tasks = [query_model(m, r, prompt, full_code_bundle) for m, r, prompt in REVIEWERS]
    results = await asyncio.gather(*tasks)

    report_lines = [
        "# Multiperspective Adversarial Review: Cohezion 4-Phase Gap-Closure Deliverables\n",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n",
        "**Evaluators**: `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`\n\n---\n",
    ]

    for r in results:
        report_lines.append(f"## Perspective: {r['model']} — {r['role']}\n\n")
        report_lines.append(r["content"].strip())
        report_lines.append("\n\n---\n")

    report_file = REPO_ROOT / "docs/research/gap_closure_adversarial_review.md"
    report_file.write_text("\n".join(report_lines))
    logger.info("✅ Saved comprehensive multiperspective adversarial review to %s", report_file)


if __name__ == "__main__":
    asyncio.run(main())
