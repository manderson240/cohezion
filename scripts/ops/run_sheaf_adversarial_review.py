#!/usr/bin/env python3
"""Adversarial Multiperspective Code Review of Sheaf Consistency Gate & Dynamic OOMGuard.

Conducts independent adversarial reviews using:
1. Headless Claude CLI (`/home/mike-anderson/.local/bin/claude`)
2. Ollama Cloud Model (`deepseek-v4-pro:cloud` on :11434)
3. Local Silicon Model (`Qwen3-Coder-30B` on :13305)
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("adversarial_review_suite")


async def run_adversarial_suite():
    logger.info("=" * 95)
    logger.info("🛡️ EXECUTING DUAL-ORACLE ADVERSARIAL CODE REVIEW (CLAUDE CLI + OLLAMA CLOUD)")
    logger.info("=" * 95)

    sheaf_code = (REPO_ROOT / "src/cohezion/governance/sheaf_consistency_gate.py").read_text(encoding="utf-8")
    oom_code = (REPO_ROOT / "src/cohezion/reliability/oom_guard.py").read_text(encoding="utf-8")

    review_prompt = f"""\
You are an adversarial, cynical Principal Verification Engineer and Mathematical Systems Architect.
Review the following production implementations:

1. SHEAF CONSISTENCY GATE (`sheaf_consistency_gate.py`):
```python
{sheaf_code}
```

2. DYNAMIC OOM GUARD & SHMEM ACCOUNTING (`oom_guard.py`):
```python
{oom_code}
```

Evaluate across the 4 Perspectives:
- Perspective A: Hardware & System Reliability (Dynamic floor formula, Shmem accounting, /proc/meminfo edge cases)
- Perspective B: Mathematical Physics & Geometry (Čech cohomology H^0 / H^1 correctness, coboundary residuals, metric space validity)
- Perspective C: Cryptography & Formal Verification (Tolerance gating, floating point precision edge cases, zero false positives)
- Perspective D: Swarm Teleology & Safety (Obstruction resolution, deadlock prevention, scalability across 100+ agents)

Provide cynical critique, edge cases, numerical scores (0.00 - 1.00), and final approval verdict.
"""

    # 1. Query Ollama Cloud deepseek-v4-pro:cloud
    logger.info("1. Querying `deepseek-v4-pro:cloud` via Ollama (:11434)...")
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            r = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "deepseek-v4-pro:cloud",
                    "prompt": review_prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 1200},
                },
            )
            cloud_content = (r.json().get("response") or r.json().get("thinking") or "").strip()
            logger.info("✓ Cloud Review complete in %.2f s.", time.perf_counter() - t0)
        except Exception as exc:
            cloud_content = f"Cloud query failed: {exc}"

    # 2. Query Headless Claude CLI
    logger.info("2. Querying Headless Claude CLI...")
    t1 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["/home/mike-anderson/.local/bin/claude", "-p", review_prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        claude_content = proc.stdout.strip()
        logger.info("✓ Claude CLI Review complete in %.2f s.", time.perf_counter() - t1)
    except Exception as exc:
        claude_content = f"Claude CLI query failed: {exc}"

    # Write combined review artifact
    artifact_path = REPO_ROOT / "docs/research/sheaf_and_oom_dual_adversarial_review.md"
    artifact_path.write_text(
        f"# Dual-Oracle Multiperspective Adversarial Code Review\n\n"
        f"## 1. DeepSeek-v4-Pro (Ollama Cloud) Review\n{cloud_content}\n\n"
        f"## 2. Claude CLI Review\n{claude_content}\n",
        encoding="utf-8",
    )
    logger.info("Saved combined review artifact to: %s", artifact_path)


if __name__ == "__main__":
    asyncio.run(run_adversarial_suite())
