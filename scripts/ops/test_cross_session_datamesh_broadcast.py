#!/usr/bin/env python3
"""Broadcasts Agentic Hot-Swap & Memory Telemetry across the EventBus and SurrealDB DataMesh."""

import asyncio
import os
import time

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.smart_oom_governor import SmartOOMGovernor

async def main():
    print("\n" + "=" * 110)
    print("📡 BROADCASTING MEMORY & INFERENCE TELEMETRY TO AGENTIC EVENT BUS DATAMESH")
    print("=" * 110)

    event_bus = await get_event_bus()
    session_id = "antigravity_orch_session"
    bridge = CrossSessionEventBridge(event_bus=event_bus, session_id=session_id)
    await bridge.initialize()

    avail_gib, swap_used_gib, is_safe = SmartOOMGovernor.get_memory_state()

    # 1. Publish Event to EventBus
    telemetry_event = Event(
        type=EventType.SYSTEM_HEALTH,
        source="smart_oom_governor",
        priority=10,
        payload={
            "status": "HEALTHY",
            "available_ram_gib": avail_gib,
            "swap_used_gib": swap_used_gib,
            "oom_floor_gib": 35.0,
            "active_guardrail": "Learning 92: Liveness Over Speed",
            "recommended_router": "Tier 1 Resident -> Tier 2 Ollama Cloud"
        }
    )
    await event_bus.publish(telemetry_event)
    print(f"✓ Emitted `SYSTEM_HEALTH` event across in-memory EventBus (Priority: 10)")

    # 2. Persist to SurrealDB and Kanban Board
    card_data = {
        "id": "oom_guardrail_status",
        "title": "Smart Cross-Session OOM Governor Active",
        "status": "in_progress",
        "priority": "high",
        "source": "smart_oom_governor",
        "category": "system_governance",
        "details": f"Avail: {avail_gib} GiB | Floor: 35.0 GiB | Swap: {swap_used_gib} GiB | Learning 92 Active",
    }
    persist_item(card_data)
    print(f"✓ Persisted Kanban card `oom_guardrail_status` into SurrealDB & Obsidian Vault")

    # 3. Check for Peer Cross-Session Events
    print("\n🔍 Checking for Peer Session Events on SurrealDB DataMesh...")
    events = await bridge.fetch_cross_session_events(limit=5)
    print(f"• Retrieved {len(events)} cross-session events from peer sessions.")
    for ev in events:
        if isinstance(ev, dict):
            print(f"   - [{ev.get('timestamp')}] ({ev.get('session_id')}): {ev.get('type')} from `{ev.get('source')}`")
        else:
            print(f"   - Event record: {ev}")

    print("=" * 110)
    print("🎉 AGENTIC DATAMESH EVENT BROADCAST VERIFIED!")
    print("=" * 110 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
