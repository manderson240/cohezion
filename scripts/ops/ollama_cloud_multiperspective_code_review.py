r"""Ollama Cloud Multiperspective Adversarial Code Review
======================================================
Delegates a 4-perspective adversarial code review of the Cohezion codebase to Tier 2
Ollama Cloud models (`deepseek-v4-pro:cloud` and `glm-5.2:cloud`):

Review Perspectives:
  1. Hardware Reliability & Memory Floor (128GB UMA / 16GB Floor).
  2. Poincare 2048D Hyperbolic Geometry & Conformal Dynamics.
  3. AutoHarness AST Bytecode Policy Safety (arXiv:2603.03329v1).
  4. Swarm Teleology & Expected Value of Intervention (EVI > 0.75).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "reviews"


def query_ollama(model: str, prompt: str) -> str:
    logger.info("=== Querying Tier 2 Ollama Cloud Model: `%s` ===", model)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            response_text = res.get("response", "").strip()
            logger.info("✓ Consultation with `%s` complete in %.2fs", model, dt)
            return response_text
    except Exception as e:
        logger.warning("! Error querying `%s`: %s", model, e)
        return f"Error querying {model}: {e}"


def main() -> None:
    code_summary = (
        "Cohezion Codebase Architecture Overview:\n"
        "1. Inference & Safety: load_safety.py, model_card_defaults.py, kv_cache_calculator.py.\n"
        "2. Core Verification: autoharness_policy.py (AST bytecode checks), zkfv_compiler.py (Plonkish gates).\n"
        "3. Swarm & Multi-Agent: EventBus, CrossSessionEventBridge, kanban_bridge.py (SurrealDB + Obsidian).\n"
        "4. Strix Halo Support: Dual-backend Vulkan0/HIP routing, 128GB UMA, 16.0 GB RAM Floor.\n"
    )

    prompt = (
        "You are acting as an Adversarial Code Review Swarm conducting a 4-perspective audit of the Cohezion codebase.\n\n"
        f"{code_summary}\n"
        "Evaluate across 4 distinct perspectives:\n"
        "1. Perspective 1 (Hardware & Memory Floor): Evaluate 128GB UMA load_safety, 16GB floor, 1.7x size factor.\n"
        "2. Perspective 2 (Poincaré & FLUME Physics): Evaluate 2048D Poincaré manifold hyperbolic distance and z-vectors.\n"
        "3. Perspective 3 (AutoHarness AST Policy): Evaluate zero-cost AST bytecode verification and 0ms latency bypass.\n"
        "4. Perspective 4 (Swarm Teleology & EVI): Evaluate EventBus inter-session bridge, SurrealDB bi-temporal logs, and EVI > 0.75.\n\n"
        "Provide a numerical score (0.0000 to 1.0000) for each perspective and an overall pass/fail determination (pass threshold >= 0.8500)."
    )

    # Delegate to Tier 2 Ollama Cloud models
    ds_review = query_ollama("deepseek-v4-pro:cloud", prompt)
    glm_review = query_ollama("glm-5.2:cloud", prompt)

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    review_path = VAULT_DIR / "OLLAMA_CLOUD_MULTIPERSPECTIVE_CODE_REVIEW.md"

    content = f"""# Ollama Cloud Multiperspective Adversarial Code Review
*Date: 2026-08-12*

## 1. DeepSeek-v4-pro Cloud Review
{ds_review}

---

## 2. GLM-5.2 Cloud Review
{glm_review}
"""
    review_path.write_text(content)
    logger.info("✅ Saved Multiperspective Adversarial Code Review to %s", review_path)


if __name__ == "__main__":
    main()
