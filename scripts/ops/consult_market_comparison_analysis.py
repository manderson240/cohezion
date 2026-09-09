r"""Ollama Cloud Oracle Consultation: Market Comparison & Competitive Strategy Analysis
========================================================================================
Consults `deepseek-v4-pro:cloud` and `glm-5.2:cloud` to perform a comprehensive market analysis
comparing Cohezion against top enterprise AI platforms, agent frameworks, and inference servers.
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
    cohezion_profile = (
        "Cohezion Architectural Profile & Benchmarks:\n"
        "- Target Category: Local Silicon Bioelectric Swarm Orchestration Platform with Systems Engineering V-Model Rigor.\n"
        "- Hardware Optimization: AMD Strix Halo 128GB UMA (1,310.5 tok/s prefill, 142.5 tok/s decode via Vulkan0/HIP Speculative Decoding).\n"
        "- Safety & Governance: Freeze-Prevention Contract (20.0GB RAM floor, 2.1x size factor, 0.00% OOM rate across 100 swaps / 20 sessions).\n"
        "- Verification Engine: 4-Tier V&V (0ms AutoHarness AST + ZK-FV SHA-256 Plonkish Proofs + R0 Multiperspective Review >= 0.8500).\n"
        "- Knowledge & Geometry: 2048D Poincaré Hyperbolic Manifolds & Anthropic 2026 J-Space Global Workspaces.\n"
        "- Dataset & Fine-Tuning: 8,644 verified instruction-response pairs mined, synthesized, and simulated through World Models.\n"
        "- Inter-Agent Infrastructure: Bidirectional EventBus RAM yield, CrossSessionEventBridge, SurrealDB 3.0 + Obsidian bi-temporal persistence.\n"
    )

    prompt = (
        "You are acting as a Senior Enterprise AI Market Analyst and Competitive Strategist.\n\n"
        f"{cohezion_profile}\n"
        "Perform a rigorous MARKET COMPARISON ANALYSIS evaluating Cohezion against:\n"
        "1. Open Source Agent Frameworks (LangChain, AutoGen, CrewAI, LlamaIndex).\n"
        "2. Enterprise AI Operating Systems & Data Mesh Platforms (Palantir AIP, Databricks Mosaic AI, C3.ai).\n"
        "3. Local & Cloud Inference Engines (Ollama, vLLM, TGI, SGLang).\n\n"
        "Cover 4 key sections:\n"
        "A. Architectural Matrix & Positioning: Compare throughput, V&V cost, memory safety, and long-horizon stability.\n"
        "B. Defensible Moats: Identify Cohezion's key technological moats (e.g. 0ms AST/ZKFV vs LLM-as-a-judge, UMA zero-copy speed, 20GB floor safety).\n"
        "C. Target Enterprise Segments & Use Cases: Air-gapped defense, financial formal compliance, edge AGI & robotics.\n"
        "D. Strategic Commercialization & Go-To-Market Roadmap.\n\n"
        "Provide a detailed, professional, executive-ready report."
    )

    ds_eval = query_ollama("deepseek-v4-pro:cloud", prompt)
    glm_eval = query_ollama("glm-5.2:cloud", prompt)

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "COHEZION_MARKET_COMPARISON_ANALYSIS.md"

    content = f"""# Cohezion Market Comparison Analysis & Competitive Strategy Report
*Date: 2026-08-13*

## 1. DeepSeek-v4-pro Market Comparison & Strategy Analysis
{ds_eval}

---

## 2. GLM-5.2 Market Comparison & Strategy Analysis
{glm_eval}
"""
    report_file.write_text(content)
    logger.info("✅ Saved Market Comparison Analysis to %s", report_file)


if __name__ == "__main__":
    main()
