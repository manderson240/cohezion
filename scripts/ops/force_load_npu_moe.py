r"""Force Load & Benchmark qwen3.6-moe-35b-a3b-FLM on NPU Lane
============================================================
Acquires `FleetLock("modelload")`, checks load safety (`check_load_safe`),
and runs direct local NPU MoE inference via Lemonade OmniRouter (port 13305).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.request

from cohezion.inference.load_safety import check_load_safe
from cohezion.researcher.daily_researcher import FleetLock
from cohezion.reliability.oom_guard import OOMGuard

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
MODEL_ID = "qwen3.6-moe-35b-a3b-FLM"


async def main() -> None:
    logger.info("🔒 Acquiring FleetLock('modelload') for NPU MoE model load...")
    flock = FleetLock()
    async with flock.acquire("modelload"):
        mem = OOMGuard.get_memory_state()
        logger.info("📡 Live Memory State: %.2f GiB available", mem.available_gb)

        ok, reason = check_load_safe({"recipe": "flm", "size": 12.0}, available_gb=mem.available_gb)
        if not ok:
            logger.warning("⚠️ Memory headroom insufficient: %s. Aborting load.", reason)
            return

        logger.info("✅ Load safety confirmed. Dispatching direct NPU MoE query to %s...", MODEL_ID)
        t0 = time.perf_counter()

        prompt = (
            "Explain how the 35B/3B Mixture-of-Experts (MoE) sparse routing architecture in "
            "qwen3.6-moe-35b-a3b-FLM achieves 10x throughput efficiency on AMD Strix Halo unified memory."
        )

        payload = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.6,
        }

        try:
            req = urllib.request.Request(
                LEMONADE_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60.0) as r:
                res = json.loads(r.read().decode())
                content = (res["choices"][0]["message"].get("content") or "").strip()
                dt_sec = time.perf_counter() - t0

                print("\n" + "=" * 90)
                print("    DIRECT LOCAL NPU MoE INFERENCE RESULTS (qwen3.6-moe-35b-a3b-FLM)")
                print("=" * 90)
                print(f"  • Model ID: {MODEL_ID}")
                print(f"  • Hardware Lane: NPU / UMA iGPU (port 13305)")
                print(f"  • Execution Time: {dt_sec:.3f} s")
                print(f"  • Output Content Snippet:\n    {content[:300]}...")
                print("=" * 90)
                print("🎉 Direct NPU MoE Model Elicitation Complete!")
        except Exception as e:
            logger.warning("NPU MoE Inference note: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
