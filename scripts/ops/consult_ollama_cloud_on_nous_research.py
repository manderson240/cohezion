#!/usr/bin/env python3
"""Consults Ollama Cloud Models to Analyze Nous Research Releases for Cohezion.

Queries `deepseek-v4-flash:0731-cloud` and `qwen3.5:397b-cloud` to evaluate:
1. Nous DisTrO (Distributed Training Optimizer) & Psyche Network.
2. Nous WorldSim (Synthetic Environment & Social Simulation).
3. Hermes 3 / Hermes Function Calling & Structured Reasoning schemas.
4. Forge Reasoning Engine & Agentic Inference Tooling.
"""

import asyncio
import json
import os
import time
import httpx

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item

OLLAMA_URL = "http://localhost:11434/api/chat"

PROMPT = """You are a Principal AI Systems Architect consulting for the Cohezion project (an autonomous AI agent platform with 12D Poincare manifolds, FLUME methodology, AutoHarness AST verification, and multi-silicon inference).

Analyze the major releases and research breakthroughs from Nous Research (https://nousresearch.com/releases):
1. DisTrO (Distributed Training Optimizer) & Psyche Decentralized Training Network.
2. Nous WorldSim (Agentic Synthetic Universe & Physics Simulation).
3. Hermes 3 / Hermes Structured Reasoning & Tool-Use Schemas.
4. Forge Reasoning API / Agentic Inference Platform.

Provide a structured, deep architectural assessment:
- What specific mathematical algorithms, protocols, or schemas should Cohezion leverage immediately?
- How can Nous WorldSim improve our FLUME Poincaré universe simulation?
- How can DisTrO/Psyche concepts help local multi-silicon (NPU, iGPU, CPU) collaborative weight updates?
- What are the concrete integration steps?
"""

async def query_cloud_model(model_name: str):
    print(f"\n▶ Consulting Ollama Cloud Model: `{model_name}` on Nous Research Releases...")
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are an elite frontier AI researcher."},
            {"role": "user", "content": PROMPT}
        ],
        "stream": False,
        "options": {"temperature": 0.3}
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            r = await client.post(OLLAMA_URL, json=payload)
            dt = round(time.perf_counter() - t0, 2)
            if r.status_code == 200:
                data = r.json()
                content = data.get("message", {}).get("content", "").strip()
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                print(f"   ✓ `{model_name}` Consultation Completed in {dt}s!")
                return content
            else:
                print(f"   ❌ Notice HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    return ""

async def main():
    print("\n" + "=" * 115)
    print("☁️ OLLAMA CLOUD STRATEGIC CONSULTATION: NOUS RESEARCH RELEASES")
    print("=" * 115)

    # Use fast cloud model for instant high-quality analysis
    model = "deepseek-v4-flash:0731-cloud"
    report_content = await query_cloud_model(model)

    if report_content:
        # Save to docs/research
        out_path = Path("docs/research/nous_research_synergy_cloud_consultation.md")
        out_path.write_text(f"# Strategic Consultation: Leveraging Nous Research in Cohezion\n\n**Generated via Ollama Cloud Model**: `{model}`\n\n" + report_content)
        print(f"\n✓ Saved strategic consultation to `{out_path}`")

        # Publish to EventBus DataMesh
        event_bus = await get_event_bus()
        bridge = CrossSessionEventBridge(event_bus=event_bus, session_id="nous_research_consultation_session")
        await bridge.initialize()

        ev = Event(
            type=EventType.CUSTOM,
            source="ollama_cloud_nous_consultant",
            priority=10,
            payload={
                "model": model,
                "target": "https://nousresearch.com/releases",
                "status": "COMPLETED",
                "topics": ["DisTrO", "WorldSim", "Hermes-3", "Forge"]
            }
        )
        await event_bus.publish(ev)

        persist_item({
            "id": "nous_research_synergy_analysis",
            "title": "Nous Research Releases Strategic Synergy Report",
            "status": "done",
            "priority": "high",
            "source": "ollama_cloud_nous_consultant",
            "category": "frontier_research",
            "details": "Ollama Cloud strategic assessment of Nous Research releases (DisTrO, WorldSim, Hermes-3, Forge) for Cohezion.",
        })
        print("✓ Dual-persisted Kanban card to SurrealDB and Obsidian Vault")

    print("\n" + "=" * 115)
    print("🏆 STRATEGIC CONSULTATION COMPLETE!")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    from pathlib import Path
    asyncio.run(main())
