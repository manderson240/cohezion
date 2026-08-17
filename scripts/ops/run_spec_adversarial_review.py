#!/usr/bin/env python3
"""Multiperspective Adversarial Code Review of Engineering Specs (`EXP-001` through `EXP-005`).

Evaluates all 5 engineering specifications and standalone blueprints across the 4 cynical perspectives:
- Perspective A: Hardware & System Reliability (NPU/iGPU memory allocation, KV-cache contention, zero crashes)
- Perspective B: Mathematical Physics & Geometry (Poincaré metric correctness, Lyapunov exponent convergence, Betti stability)
- Perspective C: Cryptography & Formal Verification (AutoHarness AST bytecode verifier safety, HMAC data provenance)
- Perspective D: Swarm Teleology & Safety (EVI thresholds, infinite loops, sovereign offline resilience)

Executes review using Tier-1 Local Silicon (`Qwen3-Coder-30B-A3B-Instruct-GGUF` via Lemonade on :13305).
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
import httpx

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spec_adversarial_review")


async def run_spec_adversarial_review():
    logger.info("=" * 90)
    logger.info("🛡️ EXECUTING MULTIPERSPECTIVE ADVERSARIAL REVIEW OF SPECS VIA LOCAL QWEN3-CODER-30B")
    logger.info("=" * 90)

    specs_dir = REPO_ROOT / "docs/specs"
    spec_files = sorted(list(specs_dir.glob("EXP-*.md")))
    logger.info("Found %d specifications under %s", len(spec_files), specs_dir)

    all_specs_content = ""
    for sf in spec_files:
        all_specs_content += f"\n\n--- SPEC: {sf.name} ---\n" + sf.read_text(encoding="utf-8")[:1500]

    prompt = f"""\
You are an adversarial, cynical Principal Verification Engineer and Frontier Systems Architect.
Perform an uncompromising 4-Perspective Adversarial Review on the following 5 Resurrectable Engineering Specifications:

ENGINEERING SPECIFICATIONS (EXP-001 to EXP-005):
{all_specs_content}

EVALUATION PERSPECTIVES:
- Perspective A: Hardware & System Reliability (NPU/iGPU memory safety, Strix Halo partitioning, non-blocking execution)
- Perspective B: Mathematical Physics & Geometry (Hyperbolic Poincaré distance formulas, Lyapunov divergence, Fréchet centroids)
- Perspective C: Cryptography & Formal Verification (AutoHarness AST bytecode zero-latency claims, SurrealDB SQL schemas)
- Perspective D: Swarm Teleology & Safety (Resurrection viability from zero dependencies, failure modes, alignment)

Provide rigorous findings for each perspective, with scores (0.00 - 1.00), specific edge-case risks identified, mitigations, and an overall verdict.
"""

    logger.info("Dispatching specs to local model `Qwen3-Coder-30B-A3B-Instruct-GGUF` on :13305...")
    t0 = time.perf_counter()

    async with httpx.AsyncClient(timeout=180.0) as client:
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
                logger.info("✓ Local Adversarial Spec Review Complete in %.2f seconds.", dt)

                out_path = REPO_ROOT / "docs/research/multiperspective_adversarial_specs_review.md"
                out_path.write_text(review_content, encoding="utf-8")
                logger.info("Saved report to: %s", out_path)
                print("\n" + "=" * 90)
                print(review_content)
                print("=" * 90 + "\n")
            else:
                logger.error("Local model returned HTTP %d: %s", r.status_code, r.text)
        except Exception as exc:
            logger.error("Failed to query local model: %s", exc)


if __name__ == "__main__":
    asyncio.run(run_spec_adversarial_review())
