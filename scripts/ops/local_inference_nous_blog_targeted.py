#!/usr/bin/env python3
"""Targeted Local Silicon Inference Analysis of Nous Research Blog.

Queries `user.cohezion-hermes-router` (:13305) with direct user prompts.
"""

import asyncio
import os
import time
import httpx
from pathlib import Path

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item

PROMPT = "Provide a 3-bullet technical summary of how Cohezion can leverage Hermes 4.3 (512k context), DeMo (Decentralized Momentum), and Psyche P2P training from the Nous Research Blog."

async def run():
    payload = {
        "model": "user.cohezion-hermes-router",
        "messages": [
            {"role": "user", "content": PROMPT}
        ],
        "temperature": 0.3,
        "max_tokens": 450
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post("http://localhost:13305/v1/chat/completions", json=payload)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            data = r.json()
            analysis = data["choices"][0]["message"]["content"].strip()
            print(f"Raw Output ({dt}s):\n{analysis}")
            
            report_path = Path("docs/research/nous_blog_local_inference_report.md")
            report_path.write_text(f"# Nous Research Blog Technical Analysis\n\n**Generated via Local Silicon**: `user.cohezion-hermes-router` (:13305)\n**Execution Latency**: {dt}s | **Cloud Cost**: $0.00\n\n" + analysis)
            print(f"✓ Saved to `{report_path}`")

if __name__ == "__main__":
    asyncio.run(run())
