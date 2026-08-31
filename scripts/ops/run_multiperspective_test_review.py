#!/usr/bin/env python3
"""Multiperspective Adversarial Review across Ollama Cloud & Local GAIA Agents.

Evaluates test suite architecture, naming refactors, and test hygiene from 4 distinct adversarial perspectives:
1. DeepSeek-V4-Pro (Tier 2 Cloud: Senior Principal QA & Compiler Architect)
2. Qwen3.5-397B (Tier 2 Cloud: Systems Verification & Security Red Team)
3. GLM-5.2 (Tier 2 Cloud: Formal Methods & Invariant Verifier)
4. Local GAIA Resident Agent (Local Silicon: Fast Execution & AST Analysis)
"""

import asyncio
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("adversarial_review_swarm")

REVIEW_TOPIC = """
Subject: Multi-perspective Adversarial Review of Test Suite Refactoring & Anti-Patterns.

Context:
In Cohezion's recent test sweep, three production/domain classes were causing PytestCollectionWarnings because they were prefixed with 'Test*':
1. `TestGenStatus` (Enum) -> Refactored to `GenerationStatus`
2. `TestMetrics` (Pydantic BaseModel) -> Refactored to `SystemVerificationReport`
3. `TestGenerator` (AST Parser Tool) -> Refactored to `CodeSuiteGenerator`

Initial Quick-Fix Attempt: Added `__test__ = False` to the class declarations.
Final Rigorous Fix: Refactored class names to eliminate the `Test*` prefix entirely, preserved backwards compatibility aliases, and updated pyproject.toml filterwarnings.

Adversarial Review Goals:
1. Identify any hidden risks, namespace collisions, or regression vectors introduced by renaming domain models vs using `__test__ = False`.
2. Critique the 107 remaining failing tests in the 12,515-test repository suite (mostly related to missing mock fixtures or live services).
3. Provide concrete recommendations for zero-flakiness, pure hermetic test execution across multi-agent swarms.
"""


async def query_ollama_model(model_name: str, perspective_role: str) -> dict:
    prompt = f"You are acting as a {perspective_role}.\n\n{REVIEW_TOPIC}\n\nProvide a sharp, critical, multiperspective adversarial review. Detail findings, risks, and recommended actions in concise Markdown."
    
    url = "http://localhost:11434/api/generate"
    data = json.dumps({"model": model_name, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}})
    
    logger.info("📡 Dispatching review prompt to %s (%s)...", model_name, perspective_role)
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, data=data.encode("utf-8"), headers={"Content-Type": "application/json"})
        loop = asyncio.get_running_loop()
        resp_data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=120.0).read().decode("utf-8"))
        res = json.loads(resp_data)
        dt = time.perf_counter() - t0
        response_text = res.get("response") or res.get("thinking") or ""
        logger.info("✓ Received review from %s in %.2fs (%d chars)", model_name, dt, len(response_text))
        return {"model": model_name, "role": perspective_role, "latency": dt, "review": response_text}
    except Exception as e:
        logger.error("❌ Failed to query %s: %s", model_name, e)
        return {"model": model_name, "role": perspective_role, "latency": 0.0, "error": str(e), "review": f"Error: {e}"}


async def main():
    logger.info("=" * 80)
    logger.info("STARTING MULTIPERSPECTIVE ADVERSARIAL REVIEW SWARM")
    logger.info("=" * 80)
    
    tasks = [
        query_ollama_model("deepseek-v4-pro:cloud", "Senior Principal QA & Compiler Architect"),
        query_ollama_model("qwen3.5:397b-cloud", "Systems Verification & Security Red Team Lead"),
        query_ollama_model("glm-5.2:cloud", "Frontier Formal Methods & Invariant Verifier"),
    ]
    
    results = await asyncio.gather(*tasks)
    
    output_md = ["# Multiperspective Adversarial Review: Test Suite Architecture & Anti-Patterns\n"]
    output_md.append(f"**Execution Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
    output_md.append("**Sovereign Evaluation Engine**: Cloud Consensus Swarm (`deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`)\n\n---\n")
    
    for r in results:
        output_md.append(f"## Perspective: {r['role']} (`{r['model']}`)\n")
        output_md.append(f"*Latency: {r.get('latency', 0):.2f}s*\n\n")
        output_md.append(r["review"].strip())
        output_md.append("\n\n---\n")
        
    report_path = REPO_ROOT / "docs/research/multiperspective_adversarial_test_review.md"
    report_path.write_text("\n".join(output_md))
    logger.info("✅ Saved multiperspective review report to %s", report_path)
    print(f"\n[REPORT_PATH]: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
