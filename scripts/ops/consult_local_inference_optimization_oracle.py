r"""Ollama Cloud Oracle Consultation: Unlocking Peak Local Inference Potential
===========================================================================
Consults `deepseek-v4-pro:cloud` and `glm-5.2:cloud` on optimizing AMD Strix Halo local inference:
1. NPU + iGPU Speculative Decoding (llama3.2-1b-FLM draft -> Nemotron 30B target).
2. FP4/FP8 Quantized KV-Cache compression (32K -> 128K context window).
3. Pipeline Parallel Silicon Splitting (NPU attention + iGPU FFN + CPU control).
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
    current_status = (
        "Current Cohezion Strix Halo Local Inference Status (128GB DDR5-5600 UMA):\n"
        "- Target Model: Nemotron 3.5 Lightning 30B ROCmFP4 (15.73 GiB GGUF weight file).\n"
        "- Performance: 1,310.5 tok/s prompt prefill, 86.0 tok/s decode on Vulkan0/HIP (ROCBLAS_USE_HIPBLASLT=1, GGML_HIP_NO_VMM=1).\n"
        "- Safety & Resiliency: 20.0 GB RAM floor, 2.1x size factor, FleetLock('modelload') single-flight mutex, 0.00% OOM rate across 10-session stress test.\n"
        "- Bi-Temporal Persistence: SurrealDB 3.0 + Obsidian Vault dual persistence.\n"
    )

    prompt = (
        "You are acting as the Chief Silicon Architect and Performance Optimization Strategist for Cohezion.\n\n"
        f"{current_status}\n"
        "We want to know: How do we unlock 100% of our local hardware potential on AMD Strix Halo?\n"
        "Specifically analyze 3 bleeding-edge techniques:\n"
        "1. Speculative Decoding with NPU Draft Models: Using lightweight draft models (e.g. llama3.2-1b-FLM on 50 TOPS XDNA2 NPU) to boost decode speed from 86 tok/s to >140 tok/s.\n"
        "2. FP4/FP8 Quantized KV-Cache Compression: Expanding context windows from 32,768 to 128,000+ tokens without RAM bloat or perplexity degradation.\n"
        "3. Pipeline Parallel Silicon Splitting: Offloading attention to NPU, FFNs to Vulkan0/HIP iGPU, and control logic to CPU in a single zero-copy UMA forward pass.\n\n"
        "Provide a high-level strategic evaluation, architectural trade-offs, and an actionable implementation blueprint."
    )

    ds_eval = query_ollama("deepseek-v4-pro:cloud", prompt)
    glm_eval = query_ollama("glm-5.2:cloud", prompt)

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "STRIX_HALO_PEAK_LOCAL_INFERENCE_ORACLE_REPORT.md"

    content = f"""# Strix Halo Peak Local Inference Optimization Oracle Report
*Date: 2026-08-13*

## 1. DeepSeek-v4-pro Strategic Evaluation & Blueprint
{ds_eval}

---

## 2. GLM-5.2 Strategic Evaluation & Blueprint
{glm_eval}
"""
    report_file.write_text(content)
    logger.info("✅ Saved Strix Halo Peak Local Inference Report to %s", report_file)


if __name__ == "__main__":
    main()
