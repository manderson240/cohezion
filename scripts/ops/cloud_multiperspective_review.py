#!/usr/bin/env python3
"""Multi-Perspective Adversarial Review via Ollama Cloud Models.

Queries 3 distinct frontier cloud models via Ollama (:11434):
1. `deepseek-v4-pro:cloud` - The Cynical Principal Systems & Reliability Architect
2. `glm-5.2:cloud`         - The Formal Verification & Mathematical Physics Auditor
3. `qwen3.5:397b-cloud`    - The Clean Code, Anti-Bloat & CI/CD Release Commander

Topic: Evaluating our Strix Halo 100% sovereign inference stack, Linux namespaces (bwrap),
OOM headroom governor (20GB floor), AST verification, and automated PR landing pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CLOUD_REVIEW] %(message)s")
logger = logging.getLogger("cloud_review")

OLLAMA_URL = "http://localhost:11434/api/generate"

PERSPECTIVES = [
    {
        "model": "deepseek-v4-pro:cloud",
        "role": "Cynical Principal Systems & Reliability Architect",
        "prompt": (
            "You are a Cynical Principal Systems Architect auditing an autonomous agent framework on AMD Strix Halo (128GB unified memory).\n"
            "The architecture uses:\n"
            "1. Local inference via Lemonade (gpt-oss-20b MXFP4 on iGPU + qwen3.6-moe on NPU) on port 13305.\n"
            "2. Unprivileged Linux Namespaces (Bubblewrap bwrap PID 2 with loopback-only network) for executing agent mutations.\n"
            "3. OOM Headroom Governor with a 20.0 GiB available RAM floor and automatic keep_alive: 0 model evictions.\n"
            "4. AutoHarness zero-cost AST bytecode verification (< 0.2ms) before execution.\n"
            "5. AutoMerge Guard for CI/CD PR landing with ruff ratchet and test_import_smoke.py.\n\n"
            "Find 3 critical vulnerabilities, aperture race conditions, or failure modes in this design and give actionable remediations."
        ),
    },
    {
        "model": "glm-5.2:cloud",
        "role": "Formal Verification & Mathematical Physics Auditor",
        "prompt": (
            "You are a Formal Verification and Mathematical Physics Auditor reviewing a sovereign AI platform.\n"
            "The system enforces:\n"
            "1. 2048D Poincaré Ball Hyperbolic Manifolds ($d_P(u, v)$ metric) with $\|x\| < 0.9999$ boundary clipping.\n"
            "2. 12-Parameter HIHO Reality Precipitation at 0.5 Coherence with 432 Hz fundamental audio field loss gradients.\n"
            "3. Bioelectric Swarm Morphogenesis ($V_mem \in [-70, -10]mV$, Gap Junction coupling $\kappa \ge 0.5$ yielding $9x$ light-cone expansion).\n"
            "4. ZK-Attested AST contracts.\n\n"
            "Identify 3 edge-case singularities, metric boundary collapses, or mathematical inconsistencies in this formulation."
        ),
    },
    {
        "model": "qwen3.5:397b-cloud",
        "role": "Clean Code, Anti-Bloat & CI/CD Release Commander",
        "prompt": (
            "You are a Senior Release Commander and Clean Code purist (Ponytail principle: minimal abstractions, zero bloat).\n"
            "Review our CI/CD landing strategy for agentic code mutations:\n"
            "1. Ephemeral Git Worktrees for concurrent agents.\n"
            "2. AST Docstring Synthesizer filling NumPy-style docs across 1,454 modules.\n"
            "3. AutoMerge Guard executing format, debt ratchet, unit tests, and import smoke before squash-merging.\n\n"
            "Identify 3 developer experience traps, git index bloat risks, or over-engineering anti-patterns in this pipeline."
        ),
    },
]


async def query_perspective(p: dict) -> dict:
    logger.info("📡 Querying %s (%s)...", p["model"], p["role"])
    payload = {
        "model": p["model"],
        "prompt": p["prompt"],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 768},
    }
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        loop = asyncio.get_running_loop()
        resp_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=90).read())
        data = json.loads(resp_bytes.decode("utf-8"))
        dt = (time.perf_counter() - t0)
        logger.info("  ✓ Received review from %s in %.2fs", p["model"], dt)
        return {
            "model": p["model"],
            "role": p["role"],
            "response": data.get("response", "").strip(),
            "duration_s": round(dt, 2),
        }
    except Exception as e:
        logger.warning("  ⚠️ Query failed for %s: %s", p["model"], e)
        return {"model": p["model"], "role": p["role"], "response": f"Failed: {e}", "duration_s": 0.0}


async def main():
    logger.info("🚀 ===================================================================")
    logger.info("🚀 OLLAMA CLOUD MULTI-PERSPECTIVE ADVERSARIAL REVIEW")
    logger.info("🚀 ===================================================================")
    
    results = await asyncio.gather(*(query_perspective(p) for p in PERSPECTIVES))
    
    # Save combined report
    report_lines = [
        "# 🛡️ Frontier Ollama Cloud Multi-Perspective Adversarial Review",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "**Substrate**: AMD Strix Halo + Ollama Cloud Fleet",
        "\n---\n",
    ]
    for r in results:
        report_lines.append(f"## 👤 {r['role']} (`{r['model']}`)")
        report_lines.append(f"*Latency: {r['duration_s']}s*\n")
        report_lines.append(r["response"])
        report_lines.append("\n---\n")

    report_content = "\n".join(report_lines)
    report_path = "/home/mike-anderson/.gemini/antigravity-cli/brain/54146dc4-dff4-4b47-a2cb-abb16f9e3812/ollama_cloud_adversarial_review.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logger.info("🎉 Multi-Perspective Review Saved to: %s", report_path)


if __name__ == "__main__":
    asyncio.run(main())
