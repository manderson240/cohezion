#!/usr/bin/env python3
"""Multi-Perspective Adversarial Review of the Sovereign Spinning Plates Protocol.

Dispatches the complete source diffs of:
1. `src/cohezion/proactive/spinning_plates_protocol.py` (Spinning Plates Engine)
2. `src/cohezion/skills/SPINNING_PLATES_PROTOCOL_PRIME.md` (PRIME Skill)
3. `scripts/ops/demo_spinning_plates_protocol.py` (Verification Harness)

To 3 distinct frontier personas in Ollama Cloud:
- Persona 1 (`deepseek-v4-pro:cloud`): "Red Team Concurrency, Memory & Subprocess Security Specialist"
- Persona 2 (`qwen3.5:397b-cloud`): "Principal Distributed Scheduling & Heterogeneous UMA Hardware Architect"
- Persona 3 (`glm-5.2:cloud`): "Formal Category Theorist & Symplectic Invariant Evaluator"
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
logger = logging.getLogger("spinning_plates_review")

REVIEWERS = [
    (
        "deepseek-v4-pro:cloud",
        "Red Team Concurrency, Memory & Subprocess Security Specialist",
        "You are an adversarial Red Team Concurrency & Security Engineer. Stress-test the Spinning Plates Governor for async task cancellation leaks, uncaught exception propagation in background tasks, UMA memory starvation, and timeout resilience.",
    ),
    (
        "qwen3.5:397b-cloud",
        "Principal Distributed Scheduling & Heterogeneous UMA Hardware Architect",
        "You are a Principal Distributed Systems & Strix Halo Hardware Architect. Adversarially critique the Spinning Plates Protocol for hardware lane oversubscription (NPU vs iGPU vs CPU), thread starvation, async sleep drift, and backpressure handling.",
    ),
    (
        "glm-5.2:cloud",
        "Formal Category Theorist & Symplectic Invariant Evaluator",
        "You are a Formal Mathematical Physicist and Category Theorist. Adversarially analyze the concurrent plate synchronization for sheaf-theoretic consistency, Fréchet mean convergence guarantees, and symplectic phase-space preservation.",
    ),
]

FILES_TO_REVIEW = [
    "src/cohezion/proactive/spinning_plates_protocol.py",
    "src/cohezion/skills/SPINNING_PLATES_PROTOCOL_PRIME.md",
    "scripts/ops/demo_spinning_plates_protocol.py",
]


async def query_model(model_name: str, role: str, persona_prompt: str, code_bundle: str) -> dict:
    logger.info("Dispatching Spinning Plates review to %s (%s)...", model_name, role)
    full_prompt = f"""{persona_prompt}

Perform an exhaustive, adversarial, and uncompromising code review of the newly implemented Cohezion Sovereign Spinning Plates Protocol.

Source Code Bundle:
{code_bundle}

Provide your structured review:
1. CRITICAL VULNERABILITIES & CONCURRENCY BOTTLENECKS (Task leaks, hardware contention, race conditions).
2. HARDWARE-UMA OR MATHEMATICAL VIOLATIONS.
3. CONCRETE HARDENING RECOMMENDATIONS (With exact code snippets).
4. FINAL ADVERSARIAL VERDICT: [APPROVED | CHANGES REQUIRED | BLOCKED]
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
    logger.info("STARTING MULTI-PERSPECTIVE ADVERSARIAL REVIEW OF SPINNING PLATES PROTOCOL")
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
        "# Multi-Perspective Adversarial Review: Sovereign Spinning Plates Protocol\n",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n",
        "**Evaluators**: `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`\n\n---\n",
    ]

    for r in results:
        report_lines.append(f"## Perspective: {r['model']} — {r['role']}\n\n")
        report_lines.append(r["content"].strip())
        report_lines.append("\n\n---\n")

    report_file = REPO_ROOT / "docs/research/spinning_plates_adversarial_review.md"
    report_file.write_text("\n".join(report_lines))
    logger.info("✅ Saved Spinning Plates adversarial review to %s", report_file)


if __name__ == "__main__":
    asyncio.run(main())
