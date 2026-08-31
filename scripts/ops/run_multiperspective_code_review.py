#!/usr/bin/env python3
"""Multiperspective Adversarial Code Review of Recent Changes (`git diff origin/main`).

Evaluates recent commits and code changes across the 4 cynical perspectives:
- Perspective A: Hardware & System Reliability (OOM safety, leaks, locks, latency)
- Perspective B: Mathematical Physics & Geometry (Poincaré metric invariants, clamping, 4-fabric metrics)
- Perspective C: Cryptography & Formal Verification (AST bytecode safety, slopsquatting, HMAC provenance)
- Perspective D: Swarm Teleology & Safety (Alignment drift, sovereign local execution, infinite loops)

Executes review using Tier-1 Local Silicon (`Qwen3-Coder-30B-A3B-Instruct-GGUF` via Lemonade on :13305).
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
import httpx

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.governance.multiperspective_review import MultiperspectiveReviewEngine
from cohezion.reliability.oom_guard import OOMGuard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("adversarial_code_review")


async def run_multiperspective_code_review():
    logger.info("=" * 90)
    logger.info("🛡️ STARTING MULTIPERSPECTIVE ADVERSARIAL CODE REVIEW (LOCAL QWEN3-CODER-30B)")
    logger.info("=" * 90)

    # 1. Inspect recent git diff
    diff_cmd = subprocess.run(
        ["git", "diff", "HEAD~5..HEAD", "--stat"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    diff_stat = diff_cmd.stdout.strip()
    logger.info("Git Diff Stat (Last 5 Commits):\n%s", diff_stat)

    # 2. Extract Key Diff Snippets
    full_diff_cmd = subprocess.run(
        ["git", "diff", "HEAD~5..HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    full_diff = full_diff_cmd.stdout[:4000]

    # 3. Local Model Adversarial Review
    prompt = f"""\
You are an adversarial, cynical Principal Software Engineer and Frontier Cryptographic Systems Auditor.
Perform a strict 4-Perspective Adversarial Code Review on the following git changes:

GIT DIFF STAT:
{diff_stat}

DIFF SAMPLE:
{full_diff}

EVALUATION PERSPECTIVES:
- Perspective A: Hardware & System Reliability (OOM guard >= 20GB, memory leaks, lock timeouts, exception handling)
- Perspective B: Mathematical Physics & Geometry (Poincaré hyperbolic metrics, clamping ||u|| <= 0.99, numerical stability)
- Perspective C: Cryptography & Formal Verification (AST bytecode safety, slopsquatting package defense, HMAC-SHA256 integrity)
- Perspective D: Swarm Teleology & Safety (Self-healing bounds, sovereign local routing, infinite loops)

Provide detailed findings for each perspective, with scores (0.00 - 1.00), specific risks identified, mitigations, and an overall verdict.
"""

    logger.info("Dispatching diff to local model `Qwen3-Coder-30B-A3B-Instruct-GGUF`...")
    t0 = time.perf_counter()

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            r = await client.post(
                "http://localhost:13305/v1/chat/completions",
                json={
                    "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1200,
                    "temperature": 0.2,
                },
            )
            if r.status_code == 200:
                dt = time.perf_counter() - t0
                msg = r.json()["choices"][0]["message"]
                review_content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
                logger.info("✓ Local Adversarial Code Review Complete in %.2f seconds.", dt)

                out_path = REPO_ROOT / "docs/research/multiperspective_adversarial_code_review.md"
                out_path.write_text(review_content, encoding="utf-8")
                logger.info("Saved report to: %s", out_path)
                print("\n" + "=" * 90)
                print(review_content)
                print("=" * 90 + "\n")
            else:
                logger.error("Local model returned HTTP %d: %s", r.status_code, r.text)
        except Exception as exc:
            logger.error("Failed to query local review model: %s", exc)


if __name__ == "__main__":
    asyncio.run(run_multiperspective_code_review())
