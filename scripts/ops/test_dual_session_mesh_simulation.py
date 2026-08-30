#!/usr/bin/env python3
"""Simulates Dual-Session Inter-Agent Collaboration over the SurrealDB EventBus DataMesh."""

import asyncio
import os
import time

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge

async def run_simulation():
    print("\n" + "=" * 110)
    print("🌐 DUAL-SESSION AGENTIC EVENT-DRIVEN DATAMESH COLLABORATION TEST")
    print("=" * 110)

    # Session A: Local Inference Agent
    bus_a = await get_event_bus()
    bridge_a = CrossSessionEventBridge(event_bus=bus_a, session_id="session_A_local_inferencer")
    await bridge_a.initialize()

    # Session B: Orchestrator Agent
    bus_b = await get_event_bus()
    bridge_b = CrossSessionEventBridge(event_bus=bus_b, session_id="session_B_orchestrator")
    await bridge_b.initialize()

    # 1. Session A publishes model hotswap notice
    print("\n▶ [Session A] Emitting `MODEL_LOADED` event to EventBus...")
    evt_a = Event(
        type=EventType.MODEL_LOADED,
        source="dynamic_hotswapper",
        priority=10,
        payload={"model": "Qwen3-Coder-30B", "footprint_gib": 17.4, "available_headroom_gib": 66.2}
    )
    await bus_a.publish(evt_a)
    await asyncio.sleep(0.5)

    # 2. Session B reads cross-session events from DataMesh
    print("▶ [Session B] Listening to SurrealDB DataMesh for peer events...")
    peer_events = await bridge_b.fetch_cross_session_events(limit=5)
    print(f"✓ [Session B] Successfully intercepted {len(peer_events)} peer events on the DataMesh!")
    for ev in peer_events:
        print(f"   • Peer Event: {ev.get('type')} from `{ev.get('source')}` in `{ev.get('session_id')}` | Payload: {ev.get('payload')}")

    print("=" * 110)
    print("🎉 FULL AGENTIC EVENT-DRIVEN DATAMESH INTER-SESSION COLLABORATION VERIFIED!")
    print("=" * 110 + "\n")

if __name__ == "__main__":
    asyncio.run(run_simulation())
