r"""Ollama Cloud Oracle Consultation: Strix Halo /r/StrixHalo Optimization Report
==============================================================================
Consults `deepseek-v4-pro:cloud` and `glm-5.2:cloud` via Ollama API (:11434) to evaluate
the latest `/r/StrixHalo` hardware optimization levers:

Community Levers Evaluated:
  1. `ROCBLAS_USE_HIPBLASLT=1`: Tuned hipBLASLt GEMM kernels yielding >1,300 t/s prefill.
  2. `-DGGML_HIP_ROCWMMA_FATTN=ON`: rocWMMA FlashAttention for Strix Halo `gfx1151`.
  3. `GGML_HIP_NO_VMM=ON`: Disabling VMM thrashing on unified 128GB memory.
  4. Dual-Backend Execution Strategy: ROCm for prefill (pp512 >1,300 t/s) + Vulkan0 (`RADV`) for decode (tg128 ~86 t/s).
  5. ROCmFP4 GGUF Quantization (`julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF`).
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
    logger.info("=== Consulting Ollama Cloud Model: `%s` ===", model)
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
    prompt = (
        "You are acting as the Lead HPC & GPU Systems Architect for Cohezion on AMD Strix Halo (Ryzen AI MAX+ 395 / gfx1151 / 128GB UMA).\n\n"
        "Evaluate the following /r/StrixHalo community discoveries & optimization levers:\n"
        "1. Dual-Backend Routing Strategy: ROCm/HIP for prompt prefill (pp512 >1,300 t/s via hipBLASLt + rocWMMA) + Vulkan0 (RADV) for decode (tg128 ~86 t/s).\n"
        "2. Environment Levers: ROCBLAS_USE_HIPBLASLT=1, -DGGML_HIP_ROCWMMA_FATTN=ON, GGML_HIP_NO_VMM=ON.\n"
        "3. ROCmFP4 GGUF Quantization: julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF running at ~4.38 bpw / 15.73 GiB footprint.\n"
        "4. Memory Safety Policy: check_load_safe with 16.0 GB RAM Floor & 1.7x size factor.\n\n"
        "Provide a strategic review on how to incorporate these levers into Cohezion's automated runtime environment."
    )

    # 1. Consult DeepSeek-v4-pro
    deepseek_res = query_ollama("deepseek-v4-pro:cloud", prompt)

    # 2. Consult GLM-5.2
    glm_res = query_ollama("glm-5.2:cloud", prompt)

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "STRIX_HALO_REDDIT_OPTIMIZATION_ORACLE.md"

    md_content = f"""# Strix Halo /r/StrixHalo Optimization Oracle Report
*Date: 2026-08-12*

## 1. DeepSeek-v4-pro Architectural Strategy
{deepseek_res}

---

## 2. GLM-5.2 Architectural Strategy
{glm_res}
"""
    report_file.write_text(md_content)
    logger.info("✅ Saved /r/StrixHalo optimization report to %s", report_file)


if __name__ == "__main__":
    main()
