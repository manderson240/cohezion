#!/usr/bin/env python3
"""Frontier Architecture & Competition Strategy Consultation with `minimax-m3:cloud`."""

import asyncio
import httpx
import json
import time
from pathlib import Path
from cohezion.core.typed_context import TypedContextStore, ContextType

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_ID = "minimax-m3:cloud"
REPORT_PATH = Path("docs/research/minimax_m3_cloud_consultation.md")

PROMPT = (
    "You are a Principal Frontier AI Systems Architect and Competitive ML Strategist running as minimax-m3:cloud. "
    "Review Cohezion's sovereign architecture across our 12-Track Kaggle portfolio and 6 core mathematical pillars:\n\n"
    "1. ARC Prize 2026 Strategy ($1.55M Pool): 2048D Hyperbolic Poincare Ball + Geodesic Neural ODEs + 0ms AutoHarness AST proof verification. "
    "Challenge: Scaling in-container Test-Time Compute (TTC) tree search to evaluate 500+ candidate DSL compositions within Kaggle's 9-hour execution envelope.\n"
    "2. Kaggriculture & Simulation Competitions ($290K Pool): 4-vCPU parallel CFR (1M rollouts) + Stochastic soil moisture MDP policy (Rank #5,235). "
    "Challenge: Reaching the #1 tier (>3,050 yield) through continuous online policy gradient optimization.\n"
    "3. Sovereign Local Hardware Architecture: AMD Strix Halo (128GB unified RAM, XDNA2 NPU, Radeon 8060S iGPU) running 5 persistent worker daemons.\n\n"
    "Deliver a structured, deep, and actionable consultation with 3 high-leverage technical recommendations to climb to 1st place."
)

async def run_minimax_consultation():
    print("\n" + "=" * 115)
    print(f"🌐 EXECUTING FRONTIER CONSULTATION WITH `{MODEL_ID}` (OLLAMA CLOUD)")
    print("=" * 115)

    store = TypedContextStore()
    store.insert(PROMPT, ContextType.INSTRUCTION, "minimax_consult_prompt")

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a Principal Frontier AI Systems Architect and Competitive ML Strategist. Provide deep, rigorous, and actionable recommendations."},
            {"role": "user", "content": PROMPT}
        ],
        "stream": False
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        t0 = time.perf_counter()
        r = await client.post(OLLAMA_URL, json=payload)
        dt = round(time.perf_counter() - t0, 2)

        if r.status_code == 200:
            msg_obj = r.json().get("message", {})
            content = msg_obj.get("content", "").strip()
            if not content and "thinking" in msg_obj:
                content = msg_obj["thinking"].strip()
            
            tool_item = store.insert(content, ContextType.TOOL_OUTPUT, f"cloud_agent:{MODEL_ID}")
            ev_item = store.transform(tool_item, ContextType.EVIDENCE, validator=lambda s: len(s) > 50)
            
            report = [
                "# MiniMax M3 (Cloud) Frontier Architecture & Competition Strategy Consultation",
                f"\n**Consultant Model:** `{MODEL_ID}`",
                f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
                f"**Latency:** {dt}s | **Typed Context Evidence ID:** `{ev_item.item_id}`",
                "\n---\n",
                content
            ]
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text("\n".join(report))
            print(f"✓ Completed in {dt}s (Evidence ID: {ev_item.item_id})")
            print(f"✓ Master Consultation Report saved to `{REPORT_PATH}`")
        else:
            print(f"❌ Error HTTP {r.status_code}: {r.text}")

    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_minimax_consultation())
