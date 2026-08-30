#!/usr/bin/env python3
"""Multi-Perspective Cloud Strategy -> Local GAIA Delegation Orchestrator.

Architecture:
1. Multi-Perspective Cloud Synthesis: Queries Tier-2 Ollama Cloud models
   (deepseek-v4-pro:cloud, qwen3.5:397b-cloud, glm-5.2:cloud) to produce distinct
   architectural proposals for genuine compound engineering refactors.
2. Structured Convergence: Synthesizes the perspectives into a verified task spec.
3. GAIA SDK Local Delegation: Dispatches the refined spec to local GAIA CLI / Lemonade (:13305)
   for 100% local silicon execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ORCHESTRATOR] %(message)s")
logger = logging.getLogger("orchestrator")

OLLAMA_API_URL = "http://localhost:11434/api/generate"
GAIA_BIN = "/home/mike-anderson/.local/bin/gaia"


@dataclass
class PerspectiveResult:
    persona: str
    model: str
    proposal: str
    duration_s: float


async def query_ollama_cloud(model: str, system_prompt: str, user_prompt: str) -> str:
    """Non-blocking query to Ollama Cloud model."""
    full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1024},
    }
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(
            OLLAMA_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        loop = asyncio.get_running_loop()
        resp_data = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=90).read().decode("utf-8")
        )
        res_json = json.loads(resp_data)
        dt = time.perf_counter() - t0
        logger.info("  ✓ Received perspective from %s in %.2fs", model, dt)
        return res_json.get("response", "")
    except Exception as e:
        logger.warning("  ✗ Failed querying %s: %s", model, e)
        return ""


async def run_multiperspective_synthesis() -> list[PerspectiveResult]:
    logger.info("🌌 ===================================================================")
    logger.info("🌌 PHASE 1: GATHERING MULTIPERSPECTIVE APPROACHES FROM OLLAMA CLOUD")
    logger.info("🌌 ===================================================================")

    perspectives = [
        {
            "persona": "Adversarial Systems Architect",
            "model": "deepseek-v4-pro:cloud",
            "system": "You are a Principal Adversarial Systems Architect specializing in autonomous agent systems and memory safety.",
            "prompt": "Propose the highest-priority, rigorous refactor for Cohezion's autonomous daemon to ensure real mutation testing with git worktrees rather than synthetic test loops.",
        },
        {
            "persona": "High-Performance Compute & ROCm Engineer",
            "model": "qwen3.5:397b-cloud",
            "system": "You are a Principal GPU Kernel & Distributed Systems Engineer specializing in AMD ROCm and memory-mapped IPC.",
            "prompt": "Propose an optimization plan to integrate POSIX /dev/shm 2048D tensor streaming into GAIA agents with sub-millisecond inter-agent communication.",
        },
        {
            "persona": "Formal Methods & Verification Lead",
            "model": "glm-5.2:cloud",
            "system": "You are a Formal Verification Lead specializing in ZK-Proofs and AutoHarness bytecode contracts.",
            "prompt": "Design an automated contract verifier that enforces AST invariant checks inside unprivileged Linux namespaces before git commits.",
        },
    ]

    tasks = [
        query_ollama_cloud(p["model"], p["system"], p["prompt"])
        for p in perspectives
    ]
    results = await asyncio.gather(*tasks)

    synthesis_list = []
    for p, res in zip(perspectives, results):
        synthesis_list.append(
            PerspectiveResult(
                persona=p["persona"],
                model=p["model"],
                proposal=res,
                duration_s=0.0,
            )
        )
    return synthesis_list


def delegate_to_gaia_local(plan_summary: str) -> str:
    logger.info("🚀 ===================================================================")
    logger.info("🚀 PHASE 2: DELEGATING CONVERGED PLAN TO LOCAL GAIA SDK / LEMONADE")
    logger.info("🚀 ===================================================================")

    prompt = (
        f"You are the GAIA Local Execution Agent running on AMD Strix Halo local silicon.\n"
        f"Here is the converged architectural plan from our multi-perspective review:\n\n"
        f"{plan_summary[:3000]}\n\n"
        f"Generate a concrete, executable Python task plan to implement this refactor locally."
    )

    t0 = time.perf_counter()
    try:
        cmd = [GAIA_BIN, "prompt", prompt]
        logger.info("Invoking GAIA CLI: %s", " ".join(cmd[:2]))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        dt = time.perf_counter() - t0
        logger.info("  ✓ GAIA Local Silicon Execution Completed in %.2fs (Return Code: %d)", dt, proc.returncode)
        output = proc.stdout if proc.returncode == 0 else proc.stderr
        return output
    except Exception as e:
        logger.warning("  ✗ Direct GAIA CLI call encountered exception: %s. Falling back to Lemonade local API...", e)
        # Fallback to local Lemonade API
        payload = {
            "model": "gpt-oss-20b-mxfp4-GGUF",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            "http://localhost:13305/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choice = data["choices"][0]["message"]
            return choice.get("content") or choice.get("reasoning_content") or ""


async def main():
    perspectives = await run_multiperspective_synthesis()
    
    # Converge proposals into executive summary
    converged_text = "# Multi-Perspective Cloud Synthesis Report\n\n"
    for p in perspectives:
        converged_text += f"## Perspective: {p.persona} ({p.model})\n"
        converged_text += f"{p.proposal.strip()}\n\n"

    # Save synthesis artifact
    out_file = "/home/mike-anderson/.gemini/antigravity-cli/brain/54146dc4-dff4-4b47-a2cb-abb16f9e3812/multiperspective_gaia_synthesis.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(converged_text)
    logger.info("✓ Saved Multi-Perspective Synthesis to %s", out_file)

    # Delegate to GAIA
    gaia_result = delegate_to_gaia_local(converged_text)
    
    # Save GAIA output
    gaia_out_file = "/home/mike-anderson/.gemini/antigravity-cli/brain/54146dc4-dff4-4b47-a2cb-abb16f9e3812/gaia_local_execution_plan.md"
    with open(gaia_out_file, "w", encoding="utf-8") as f:
        f.write(f"# GAIA SDK Local Silicon Execution Plan\n\n{gaia_result.strip()}")
    logger.info("✓ Saved GAIA Execution Plan to %s", gaia_out_file)


if __name__ == "__main__":
    asyncio.run(main())
