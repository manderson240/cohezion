r"""Ollama Cloud Oracle Consultation: Multiperspective Adversarial Code Review
=============================================================================
Consults `deepseek-v4-pro:cloud` and `glm-5.2:cloud` to perform a rigorous
multiperspective adversarial code review of all core modules built during this session.
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
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "research"


def query_ollama(model: str, prompt: str) -> str:
    logger.info("=== Consulting Ollama Cloud Review Oracle: `%s` ===", model)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            response_text = res.get("response", "").strip()
            logger.info("✓ Review with `%s` complete in %.2fs", model, dt)
            return response_text
    except Exception as e:
        logger.warning("! Error querying `%s`: %s", model, e)
        return f"Error querying {model}: {e}"


def main() -> None:
    code_summary = (
        "Cohezion Newly Implemented Core Subsystems:\n"
        "1. `src/cohezion/core/grand_unified_wiring_bus.py`: Interconnects Bioelectric Swarm (AGENT_ERROR), HIHO Sonifier (METRIC_UPDATE), Poincaré Visualizer (DATA_PRODUCT_UPDATED), and Kaggle AutoHarness into AutoHarnessPolicy.\n"
        "2. `src/cohezion/flume/monadic_markov_trace_engine.py`: Implements Result Monad (`unit`, `bind`), 5x5 Markov Stream Transition Matrix, and Recursive Trajectory Tree Back-Linking.\n"
        "3. `src/cohezion/data_mesh/multi_session_sanitization_gateway.py`: Applies 4-layer data sanitization and DPO preference pair generation across active inter-session agent swarms.\n"
        "4. `src/cohezion/agi/negative_feedback_sanitizer.py`: AutoHarness pre-quarantine, DPO preference inversion, Poincaré geodesic anomaly detection (d_P > 2.5), and checkpoint rollback.\n"
        "5. `src/cohezion/data_mesh/fleet_autotuning_datamesh_consumer.py`: Connects fleet auto-tuning daemon to DataMesh event bus.\n"
        "6. `src/cohezion/agi/fleet_autotuning_daemon.py`: Continuous QLoRA auto-tuning daemon for 5 local fleet models.\n"
    )

    prompt = (
        "You are acting as a Lead Systems Architect, Principal Security Auditor, and Senior Code Reviewer.\n\n"
        f"{code_summary}\n"
        "MULTIPERSPECTIVE ADVERSARIAL CODE REVIEW REQUEST:\n"
        "Conduct a rigorous code review across 4 expert perspectives:\n"
        "1. Systems Architect Perspective: Architecture symmetry, separation of concerns, and async event bus performance.\n"
        "2. Reliability & Resilience Perspective: Error handling, OOM safety, memory leakage, and circuit breaker fallback.\n"
        "3. Security & Safety Perspective: Input sanitization, injection defense, state isolation, and zero-knowledge verification validity.\n"
        "4. Mathematical & Theoretical Perspective: Correctness of Monad operators (`unit`, `bind`), Markov transition matrices (pi P = pi), and Poincaré geodesic bounds.\n\n"
        "Provide your overall Multiperspective Code Quality Score (0.0 to 1.0) and final sign-off verdict."
    )

    ds_review = query_ollama("deepseek-v4-pro:cloud", prompt)
    glm_review = query_ollama("glm-5.2:cloud", prompt)

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "MULTIPERSPECTIVE_ADVERSARIAL_CODE_REVIEW_REPORT.md"

    content = f"""# Cohezion Multiperspective Adversarial Code Review Report
*Date: 2026-08-13*

## 1. DeepSeek-v4-pro Adversarial Code Review
{ds_review}

---

## 2. GLM-5.2 Adversarial Code Review
{glm_review}
"""
    report_file.write_text(content)
    logger.info("✅ Saved Multiperspective Adversarial Code Review Report to %s", report_file)


if __name__ == "__main__":
    main()
