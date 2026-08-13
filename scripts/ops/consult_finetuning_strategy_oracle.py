r"""Ollama Cloud Oracle Consultation: LoRA Fine-Tuning Dataset & Hyperparameter Strategy
========================================================================================
Consults `deepseek-v4-pro:cloud` and `glm-5.2:cloud` on evaluating Cohezion's 1,644 verified instruction pairs dataset
and formulating an optimal QLoRA fine-tuning recipe for local models (`Qwen3-Coder-30B` / `Nemotron 3.5 30B`).
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
    logger.info("=== Consulting Ollama Cloud Oracle: `%s` ===", model)
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
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            response_text = res.get("response", "").strip()
            logger.info("✓ Consultation with `%s` complete in %.2fs", model, dt)
            return response_text
    except Exception as e:
        logger.warning("! Error querying `%s`: %s", model, e)
        return f"Error querying {model}: {e}"


def main() -> None:
    dataset_status = (
        "Cohezion Fine-Tuning Dataset Status:\n"
        "- Extracted: 1,644 high-quality, verified instruction-response pairs mined from Git commits, task logs, PRIME skills, and retrospectives.\n"
        "- Verification Gating: All entries verified via 0ms AutoHarness AST checks, ZK-FV SHA-256 formal proofs, and R0 Multiperspective score (>= 0.8500).\n"
        "- Target Models for Fine-Tuning: Qwen3-Coder-30B or Nemotron 3.5 Lightning 30B ROCmFP4 on AMD Strix Halo (128GB UMA / RX 7700S iGPU).\n"
    )

    prompt = (
        "You are acting as the Chief AI Training & Alignment Strategist for Cohezion.\n\n"
        f"{dataset_status}\n"
        "Analyze whether 1,644 verified instruction pairs is a meaningful dataset size for domain-adapting a 30B parameter model.\n"
        "Specifically address 3 key questions:\n"
        "1. Is 1,644 pairs meaningful? Contrast small curated datasets (LIMA paradigm) vs massive noisy SFT datasets for specialized agent alignment.\n"
        "2. What is the optimal QLoRA fine-tuning recipe? Specify Rank (r), Alpha, Learning Rate, Quantization (NF4/FP4), and target projection matrices (q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj, down_proj).\n"
        "3. What are the concrete benefits for Cohezion? Quantify system prompt context savings, AST compliance improvement, and zero-copy inference throughput.\n\n"
        "Provide a high-level strategic evaluation and an actionable training recipe."
    )

    ds_eval = query_ollama("deepseek-v4-pro:cloud", prompt)
    glm_eval = query_ollama("glm-5.2:cloud", prompt)

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "COHEZION_FINETUNING_STRATEGY_ORACLE_REPORT.md"

    content = f"""# Cohezion Fine-Tuning Strategy Oracle Report
*Date: 2026-08-13*

## 1. DeepSeek-v4-pro Fine-Tuning Evaluation & QLoRA Recipe
{ds_eval}

---

## 2. GLM-5.2 Fine-Tuning Evaluation & QLoRA Recipe
{glm_eval}
"""
    report_file.write_text(content)
    logger.info("✅ Saved Fine-Tuning Strategy Oracle Report to %s", report_file)


if __name__ == "__main__":
    main()
