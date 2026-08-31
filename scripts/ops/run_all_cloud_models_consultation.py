#!/usr/bin/env python3
"""Grand Council: Multi-Perspective Consultation Across All 13 Ollama Cloud Models.

Dispatches a unified frontier AGI architectural query across the entire 13-model Ollama Cloud roster:
1. `deepseek-v4-pro:cloud` (1.6T MoE Reasoning)
2. `qwen3.5:397b-cloud` (397B Distributed Coder)
3. `kimi-k3:cloud` (Autonomous Deep Reasoning)
4. `kimi-k2.7-code:cloud` (Agentic Tool & Code Repair)
5. `glm-5.2:cloud` (Multimodal Topology & Category Theory)
6. `nemotron-3-ultra:cloud` (Frontier Enterprise Research)
7. `nemotron-3-super:cloud` (Frontier Science & Math)
8. `minimax-m3:cloud` (Nuanced Narrative & PRD Synthesis)
9. `kimi-k2.6:cloud` (2M Context Window Architecture)
10. `deepseek-v4-flash:cloud` (High-Throughput Flash)
11. `deepseek-v4-flash:0731-cloud` (Sub-Second Low-Latency Draft)
12. `gemma4:31b-cloud` (Dense Semantic Vectors)
13. `gpt-oss:120b-cloud` (Transparent Open General Intelligence)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("all_cloud_models_consultation")

MODELS = [
    ("deepseek-v4-pro:cloud", "1.6T MoE Formal Reasoning & Red Team Security"),
    ("qwen3.5:397b-cloud", "397B Distributed Systems & Heterogeneous UMA Architecture"),
    ("kimi-k3:cloud", "Autonomous Deep Reasoning & Proof Synthesis"),
    ("kimi-k2.7-code:cloud", "Agentic Tool Verification & Patch Engineering"),
    ("glm-5.2:cloud", "Multimodal Sheaf Topology & Geometric Category Theory"),
    ("nemotron-3-ultra:cloud", "Frontier Enterprise Synthesis & Knowledge Mesh"),
    ("nemotron-3-super:cloud", "Frontier Non-Equilibrium Physics & Mathematical Validation"),
    ("minimax-m3:cloud", "Nuanced Cognitive Narrative & UX Intent Modeling"),
    ("kimi-k2.6:cloud", "2M Context Window Whole-Corpus Archaeology"),
    ("deepseek-v4-flash:cloud", "High-Throughput Real-Time Semantic Retrieval"),
    ("deepseek-v4-flash:0731-cloud", "Sub-Second Low-Latency Intent Dispatch"),
    ("gemma4:31b-cloud", "Dense High-Dimensional Semantic Vector Topology"),
    ("gpt-oss:120b-cloud", "Transparent Open General Intelligence"),
]

PROMPT = """You are acting as an elite member of the Cohezion Grand Architectural Council.

We have built a sovereign, local-first AGI framework with:
1. Spinning Plates Protocol (Zero idle local silicon on AMD Strix Halo NPU/iGPU/CPU).
2. Phoenix Architecture & Disposable Code (S_spec -> AutoHarness 0ms AST -> Code_new).
3. Dynamic Atomic Model Hot-Swapping under FleetLock("modelload") mutex.
4. Tiered Hybrid Router (Lemonade Local Silicon -> Ollama Cloud -> Kanban Dual-Persistence).

From your distinct architectural perspective, provide:
1. YOUR UNIQUE PERSPECTIVE & STRATEGIC RATIONALE (Why your model's domain expertise matters to this architecture).
2. ONE CRITICAL RISK OR BLIND SPOT (The single highest-leverage failure mode we must safeguard).
3. ONE BOLD FRONTIER RECOMMENDATION (A breakthrough capability or experiment to attempt next).
(Keep your entire response concise, sharp, and high signal-to-noise: 3-4 structured bullet points).
"""


async def query_model(model_name: str, role: str) -> dict:
    logger.info("Querying %s (%s)...", model_name, role)
    t0 = time.perf_counter()
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": PROMPT,
        "stream": False,
        "options": {"temperature": 0.2, "top_p": 0.9}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    loop = asyncio.get_running_loop()
    try:
        def _fetch():
            with urllib.request.urlopen(req, timeout=90.0) as r:
                return r.read().decode("utf-8")
        resp_data = await loop.run_in_executor(None, _fetch)
        res = json.loads(resp_data)
        content = (res.get("response") or res.get("thinking") or "").strip()
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return {"model": model_name, "role": role, "content": content, "latency_ms": round(dt_ms, 2), "success": True}
    except Exception as exc:
        logger.error("Error with %s: %s", model_name, exc)
        return {"model": model_name, "role": role, "content": f"Query Error: {exc}", "latency_ms": 0.0, "success": False}


async def main():
    logger.info("=" * 90)
    logger.info("INITIATING GRAND ARCHITECTURAL COUNCIL ACROSS ALL 13 OLLAMA CLOUD MODELS")
    logger.info("=" * 90)

    tasks = [query_model(m, r) for m, r in MODELS]
    results = await asyncio.gather(*tasks)

    report_lines = [
        "# Grand Architectural Council: Complete 13-Model Ollama Cloud Synthesis\n",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n",
        f"**Council Size**: {len(MODELS)} Frontier Models Consulted Concurrently\n\n---\n",
    ]

    for r in results:
        status_icon = "🟢" if r["success"] else "🔴"
        report_lines.append(f"## {status_icon} Perspective: `{r['model']}` — {r['role']} ({r['latency_ms']} ms)\n\n")
        report_lines.append(r["content"])
        report_lines.append("\n\n---\n")

    report_path = REPO_ROOT / "docs/research/grand_council_all_cloud_models.md"
    report_path.write_text("\n".join(report_lines))
    logger.info("✅ Saved Grand Architectural Council Report to %s", report_path)


if __name__ == "__main__":
    asyncio.run(main())
