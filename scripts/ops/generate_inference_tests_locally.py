#!/usr/bin/env python3
"""Local Inference Code Generation & Test Refactor Agent.

Uses our local resident champion model `Qwen3-Coder-30B-A3B-Instruct-GGUF`
via Lemonade Server (:13305) to generate and implement `tests/inference/test_unified_hybrid_router.py`.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
import httpx

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("local_test_generator")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
MODEL_ID = "Qwen3-Coder-30B-A3B-Instruct-GGUF"


async def generate_inference_test():
    prompt = """\
Write a complete pytest test file `tests/inference/test_unified_hybrid_router.py` for Cohezion's `UnifiedHybridRouter`.
The test file must test:
1. `test_route_by_capability_tier1_local_success`: Tests routing a reasoning prompt to local Tier 1 (deepseek-r1-0528-8b-FLM) when Lemonade is healthy.
2. `test_route_by_capability_coding_igpu`: Tests routing a coding prompt to Tier 1 Qwen3-Coder-30B-A3B-Instruct-GGUF.
3. `test_route_by_capability_tier2_cloud_fallback`: Tests falling back to Tier 2 Ollama cloud when local Tier 1 preflight fails or force_cloud=True.
4. `test_route_by_capability_embeddings`: Tests routing TaskClass.EMBEDDINGS to local embed-gemma-300m-FLM.
5. `test_route_by_capability_oom_guard_trigger`: Tests that when OOMGuard reports memory unsafe (is_safe=False), it safely routes to Tier 2 instead of crashing.

Use pytest, unittest.mock (patch, AsyncMock), MemoryState with available_gb, total_gb, swap_used_gb, shmem_gb, is_safe, dynamic_floor_gb.
Output ONLY the pure Python code within ```python ``` block.
"""

    logger.info("Querying local model `%s` via Lemonade on port 13305...", MODEL_ID)
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            LEMONADE_URL,
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1200,
                "temperature": 0.1,
            },
        )
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        logger.info("Received generated test code from local Qwen3-Coder (%d chars).", len(content))

        if "```python" in content:
            code = content.split("```python")[1].split("```")[0].strip()
        elif "```" in content:
            code = content.split("```")[1].split("```")[0].strip()
        else:
            code = content.strip()

        target_file = REPO_ROOT / "tests/inference/test_unified_hybrid_router.py"
        target_file.write_text(code + "\n", encoding="utf-8")
        logger.info("Saved local AI-generated test file to: %s", target_file)


if __name__ == "__main__":
    asyncio.run(generate_inference_test())
