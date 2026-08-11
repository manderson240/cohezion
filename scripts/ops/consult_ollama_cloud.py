#!/usr/bin/env python3
"""
Ollama Cloud Model Consultation Script
======================================
Consults `deepseek-v4-pro:cloud` and `glm-5.2:cloud` via Ollama API (:11434) to conduct
an expert second-opinion audit ("Oracle") on Cohezion's AGI & Poincaré Manifold architecture.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "research"


def query_ollama(model: str, prompt: str) -> str:
    print(f"=== Consulting Ollama Cloud Model: `{model}` ===")
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
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            response_text = res.get("response", "").strip()
            print(f"  ✓ Consultation with `{model}` complete in {dt}s")
            return response_text
    except Exception as e:
        print(f"! Error querying `{model}`:", e)
        return f"Error querying {model}: {e}"


def main():
    prompt = (
        "You are acting as the Oracle Expert Advisor for Cohezion, an AI swarm platform.\n"
        "Review our recent technical accomplishments:\n"
        "1. 256D J-Space & 2048D Poincaré Hyperbolic Manifolds with Levi-Civita Connections Gamma^k_{ij}.\n"
        "2. AutoHarness Policy AST Bytecode Compiler (arXiv:2603.03329v1) executing in < 100 microseconds.\n"
        "3. THUNLP ProactiveAgent (ICLR 2025) Human-Preference Reward Model & Expected Value of Intervention (EVI).\n"
        "4. 1,000-Step 10x Scale Experiment with 0 memory leaks across 128GB Unified Memory.\n\n"
        "Provide a high-level strategic evaluation of our progress, highlight potential blind spots, "
        "and recommend 3 next-generation technical breakthroughs for our AGI roadmap."
    )

    # 1. Consult DeepSeek-v4-pro
    deepseek_res = query_ollama("deepseek-v4-pro:cloud", prompt)

    # 2. Consult GLM-5.2
    glm_res = query_ollama("glm-5.2:cloud", prompt)

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "OLLAMA_CLOUD_CONSULTATION_ORACLE.md"

    md_content = f"""# Ollama Cloud Oracle Consultation Report
*Date: 2026-08-03*

## 1. DeepSeek-v4-pro Consultation Analysis
{deepseek_res}

---

## 2. GLM-5.2 Consultation Analysis
{glm_res}
"""
    report_file.write_text(md_content)
    print(f"\n✅ Oracle Consultation Report written to Vault: {report_file}")


if __name__ == "__main__":
    main()
