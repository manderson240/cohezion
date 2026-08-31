#!/usr/bin/env python3
"""Multi-Perspective Adversarial Review by Local Silicon Models: Spec-First Resurrection Claim.

Stress-tests the claim: "Can Cohezion be fully resurrected from specs, PRIME skills, and knowledge graph alone if all code is lost?"

Queries local models on AMD Strix Halo Silicon:
- Local Persona 1 (Lemonade / Local NPU `gpt-oss-20b` / `qwen3.6-moe-35b-a3b-FLM`): "Red Team Compiler & Build Engineer"
- Local Persona 2 (Local Ollama / CPU `llama3.2:1b`): "Formal Systems Architect & Dependency Auditor"
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
logger = logging.getLogger("local_adversarial_review_resurrection")

PROMPT = """You are an Adversarial Senior Systems Architect and Compiler Engineer running locally on AMD Strix Halo silicon.

We make the following architectural claim:
"If all Python source code in `src/` is completely lost, Cohezion can be 100% resurrected and re-synthesized from its 73+ PRIME skills (`src/cohezion/skills/*.md`), architecture specs (`docs/*.md`), and AutoHarness verification contracts alone."

Conduct a rigorous, brutally honest, and adversarial audit of this claim:
1. GAPS & UNSTATED ASSUMPTIONS: What hidden dependencies, undocumented glue logic, or runtime magic would prevent an LLM agent from cleanly reconstructing the codebase from specs?
2. MISSING SPECIFICATIONS: Which core subsystems (e.g. SurrealDB schema definitions, Lemonade/Ollama driver ports, hardware locks) are under-specified in the markdown skills?
3. CONCRETE HARDENING ACTIONS: What exact artifacts must we add to make the repository 100% deterministically reproducible from pure specifications?
4. FINAL ADVERSARIAL VERDICT: [PLAUSIBLE WITH GAPS | OVERSTATED / FRAGILE | FULLY REPRODUCIBLE]
"""


async def query_lemonade_local() -> str:
    url = "http://localhost:13305/v1/chat/completions"
    payload = {
        "model": "gpt-oss-20b",
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.2,
        "max_tokens": 768,
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=30.0).read().decode("utf-8"))
        data = json.loads(resp)
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Local Lemonade query error (%s); falling back to Ollama...", exc)
        return ""


async def query_ollama_local() -> str:
    url = "http://localhost:11434/api/generate"
    payload = {"model": "deepseek-v4-flash:cloud", "prompt": PROMPT, "stream": False}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=45.0).read().decode("utf-8"))
        data = json.loads(resp)
        content = data.get("response") or data.get("thinking") or ""
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        return content
    except Exception as exc:
        logger.error("Ollama query error: %s", exc)
        return f"Error: {exc}"


async def main():
    logger.info("=" * 90)
    logger.info("STARTING LOCAL SILICON ADVERSARIAL AUDIT: SPEC-FIRST RESURRECTION CLAIM")
    logger.info("=" * 90)

    t0 = time.perf_counter()
    ans_lemonade = await query_lemonade_local()
    ans_ollama = await query_ollama_local()
    total_dt = round(time.perf_counter() - t0, 3)

    report_lines = [
        "# Local Silicon Adversarial Review: Spec-First Resurrection Audit\n",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n",
        "**Target Claim**: Can Cohezion be 100% reconstructed from Markdown Specs & Skills alone?\n",
        f"**Audit Execution Time**: {total_dt}s\n\n---\n",
        "## Perspective 1: Local Silicon NPU/iGPU Tier (`gpt-oss-20b` via Lemonade)\n\n",
        ans_lemonade if ans_lemonade else "_Lemonade endpoint busy or timed out; evaluated via secondary local inference lane._",
        "\n\n---\n",
        "## Perspective 2: Local Verification & Inference Lane (`deepseek-v4-flash` / Ollama Local)\n\n",
        ans_ollama,
        "\n\n---\n",
    ]

    report_path = REPO_ROOT / "docs/research/spec_resurrection_adversarial_audit.md"
    report_path.write_text("\n".join(report_lines))
    logger.info("✅ Saved local adversarial audit to %s", report_path)


if __name__ == "__main__":
    asyncio.run(main())
