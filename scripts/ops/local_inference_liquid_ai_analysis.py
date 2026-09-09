#!/usr/bin/env python3
"""Local Silicon Inference Analysis of Liquid AI (https://www.liquid.ai/).

Queries `user.cohezion-hermes-router` (:13305) on AMD Strix Halo to analyze:
1. Liquid Foundation Models (LFM & LFM2.5): Non-transformer continuous-time dynamical architectures.
2. Device-Native Efficiency: Sub-millisecond latency on SLM tiers (230M, 350M, 1.2B, 2.6B).
3. Integration with Cohezion's Neural ODEs, Poincaré Geodesics, and NPU routing.
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
from cohezion.inference.smart_oom_governor import SmartOOMGovernor

PROMPT = "Provide a 3-bullet technical analysis of how Cohezion can leverage Liquid AI (https://www.liquid.ai/), Liquid Foundation Models (LFM2.5), continuous-time dynamical systems, and edge-native agentic SLMs for our AMD Strix Halo NPU/iGPU architecture."

async def run_analysis():
    print("\n" + "=" * 115)
    print("💧 LOCAL SILICON INFERENCE ANALYSIS: LIQUID AI (https://www.liquid.ai/)")
    print("=" * 115)

    # 1. System Headroom
    avail_gib, swap_used_gib, is_safe = SmartOOMGovernor.get_memory_state()
    print(f"\n▶ [1/3] Memory Governor Check:")
    print(f"   • UMA Memory Available: {avail_gib} GiB (Floor: 35.0 GiB)")
    print(f"   • Swap Used:           {swap_used_gib} GiB")
    print(f"   • Execution Status:    {'NOMINAL' if is_safe else 'BACKPRESSURE'}")

    # 2. Local Silicon Inference Call
    print(f"\n▶ [2/3] Querying Local Silicon Gateway (:13305)...")
    payload = {
        "model": "user.cohezion-hermes-router",
        "messages": [
            {"role": "user", "content": PROMPT}
        ],
        "temperature": 0.2,
        "max_tokens": 400
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post("http://localhost:13305/v1/chat/completions", json=payload)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            analysis = r.json()["choices"][0]["message"]["content"].strip()
            print(f"   ✓ Local Silicon Responded in {dt}s!")
            print(f"   • Analysis Sample:\n{analysis[:250]}...\n")

            report_path = Path("docs/research/liquid_ai_local_inference_report.md")
            report_path.write_text(f"# Liquid AI Technical Analysis\n\n**Source**: https://www.liquid.ai/\n**Generated via Local Silicon**: `user.cohezion-hermes-router` (:13305)\n**Execution Latency**: {dt}s | **Memory Headroom**: {avail_gib} GiB\n\n" + analysis)
            print(f"   ✓ Saved report to `{report_path}`")
        else:
            print(f"   ❌ Error HTTP {r.status_code}: {r.text[:150]}")
            return

    # 3. Publish to EventBus DataMesh
    print(f"\n▶ [3/3] Emitting Telemetry to EventBus DataMesh...")
    event_bus = await get_event_bus()
    session_id = "liquid_ai_research_session"
    bridge = CrossSessionEventBridge(event_bus=event_bus, session_id=session_id)
    await bridge.initialize()

    ev = Event(
        type=EventType.CUSTOM,
        source="liquid_ai_local_researcher",
        priority=10,
        payload={
            "target": "https://www.liquid.ai/",
            "topic": "Liquid Foundation Models (LFM2.5)",
            "latency_sec": dt,
            "headroom_gib": avail_gib,
            "status": "COMPLETED"
        }
    )
    await event_bus.publish(ev)

    persist_item({
        "id": "liquid_ai_research_status",
        "title": "Liquid AI & LFM2.5 Local Analysis Complete",
        "status": "done",
        "priority": "high",
        "source": "liquid_ai_local_researcher",
        "category": "frontier_research",
        "details": f"Local silicon analysis of Liquid Foundation Models (LFM2.5) for NPU/iGPU edge deployment. Latency: {dt}s.",
    })
    print("   ✓ Dual-persisted Kanban card to SurrealDB and Obsidian Vault!")

    print("\n" + "=" * 115)
    print("🏆 LIQUID AI LOCAL SILICON RESEARCH COMPLETE!")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_analysis())
