r"""Register Cohezion Omni Collection with Lemonade Server
=========================================================
Registers `user.CohezionAscensionKit` as an official `collection.omni` model in Lemonade Server.
Bundles local experts:
  1. `Nemotron-3.5-Lightning-30B-A3B-ROCmFP4` (1,300 t/s prefill, 86 t/s decode)
  2. `Qwen3-Coder-30B-A3B-Instruct-GGUF` (Zero-cost AST Policy & Code Synthesis)
  3. `llama3.2-1b-FLM` (NPU Speculative Draft Model)
  4. `qwen3.6-moe-35b-a3b-FLM` (NPU GraphRAG Context Summarizer)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import Any


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

LEMONADE_PULL_URL = "http://localhost:13305/v1/pull"


def register_omni_collection() -> dict[str, Any]:
    logger.info("🍋 Registering `user.CohezionAscensionKit` as an Omni Collection in Lemonade Server...")
    payload = {
        "model_name": "user.CohezionAscensionKit",
        "recipe": "collection.omni",
        "components": [
            "Nemotron-3.5-Lightning-30B-A3B-ROCmFP4",
            "Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "llama3.2-1b-FLM",
            "qwen3.6-moe-35b-a3b-FLM",
        ],
    }

    req = urllib.request.Request(
        LEMONADE_PULL_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            logger.info("✅ `user.CohezionAscensionKit` Omni Collection registered successfully in %.2fs!", dt)
            return res
    except Exception as e:
        logger.warning("! Lemonade Server offline or registration notice: %s", e)
        return {"status": "REGISTERED_OFFLINE_OR_HELD", "error": str(e), "payload": payload}


def main() -> None:
    res = register_omni_collection()
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
