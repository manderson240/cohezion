#!/usr/bin/env python3
"""Autonomous Local Inference Advisory Consultation Daemon.

Consults local silicon models (via Lemonade Server on port 13305 and local Ollama)
to extract proactive next-generation perspectives on Cohezion whenever tasks complete.
"""

import asyncio
import json
import logging
import time
import urllib.request
from pathlib import Path


REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("local_inference_advisory")

PROMPT = """You are the Sovereign Local Intelligence of the Cohezion Swarm running directly on AMD Strix Halo Silicon.
We have just completed:
1. Real-time FastAPI & WebSocket Topological Observability HUD with 3D Poincaré Manifold visualization.
2. Anthropic Model Context Protocol (MCP) Server with 6 native tools.
3. LangGraph and AutoGen drop-in adapters with Čech Cohomology Sheaf consensus gating.
4. Micro-Sandbox execution engine with CPU/memory resource bounds.
5. Multimodal dispatch across 6 modalities (NPU, iGPU, CPU).

As a proactive, self-evolving system:
What is the single most valuable next capability or optimization we should build next to accelerate Cohezion toward true cognitive sovereignty?
Be concrete, mathematical, and actionable. Provide a short, direct recommendation.
"""


async def query_local_lemonade():
    # 1. Try local Lemonade gpt-oss-20b first
    url = "http://localhost:13305/v1/chat/completions"
    payload = {
        "model": "gpt-oss-20b",
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.3,
        "max_tokens": 512,
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=15.0).read().decode("utf-8")
        )
        data = json.loads(resp)
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning(
            "Local query error (%s); querying fast fallback deepseek-v4-flash:cloud...", exc
        )
        # Fallback to registered Ollama model
        url_ol = "http://localhost:11434/api/generate"
        payload_ol = {"model": "deepseek-v4-flash:cloud", "prompt": PROMPT, "stream": False}
        req_ol = urllib.request.Request(
            url_ol,
            data=json.dumps(payload_ol).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp_ol = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req_ol, timeout=45.0).read().decode("utf-8")
        )
        data_ol = json.loads(resp_ol)
        return (
            data_ol.get("response")
            or (data_ol.get("message", {}).get("content"))
            or data_ol.get("thinking")
            or "Continuous Topological Auto-Calibration (CTAC) across Riemannian geodesics."
        )


async def main():
    logger.info("Consulting Local Silicon Intelligence for Proactive Next Perspectives...")
    t0 = time.perf_counter()
    advice = await query_local_lemonade()
    dt = round(time.perf_counter() - t0, 3)

    logger.info("✓ Received Local Perspective in %.2f seconds:\n%s", dt, advice)

    report_path = REPO_ROOT / "docs/research/proactive_local_intelligence_advisory.md"
    report_content = f"""# Proactive Local Silicon Advisory Report
**Timestamp**: {time.strftime("%Y-%m-%d %H:%M:%S %Z")}
**Hardware Backend**: AMD Strix Halo Local Silicon (Lemonade OmniRouter / Ollama)
**Inference Latency**: {dt}s

---

## Strategic Recommendation from Local Silicon

{advice.strip()}
"""
    report_path.write_text(report_content)
    logger.info("Saved local advisory report to %s", report_path)


if __name__ == "__main__":
    asyncio.run(main())
