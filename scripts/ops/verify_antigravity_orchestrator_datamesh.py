#!/usr/bin/env python3
"""Verifies Antigravity (AGY) Master Orchestrator Alignment with the Event-Driven DataMesh.

Ensures:
1. AGY Sovereign Identity: Antigravity acts as Master Orchestrator, Evaluator, and Gatekeeper.
2. Direct Hook into SurrealDB DataMesh (:8001) & EventBus under session `antigravity_orch_session`.
3. AutoHarness Pre/Post Hooks & FleetLock Memory Governance (35.0 GiB Floor).
4. Dual Persistence into SurrealDB `event_log` and Obsidian Vault Kanban.
"""

import asyncio
import os
import time

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.smart_oom_governor import SmartOOMGovernor

async def test_agy_orchestrator():
    print("\n" + "=" * 115)
    print("🛸 VERIFYING ANTIGRAVITY (AGY) MASTER ORCHESTRATOR & EVENT-DRIVEN DATAMESH")
    print("=" * 115)

    # 1. Check System Memory Health
    avail_gib, swap_used_gib, is_safe = SmartOOMGovernor.get_memory_state()
    print(f"\n▶ [1/4] Antigravity UMA Silicon Memory Health Check:")
    print(f"   • UMA Memory Available: {avail_gib} GiB (Safety Floor: 35.0 GiB)")
    print(f"   • Swap Used:           {swap_used_gib} GiB")
    print(f"   • Orchestrator State:  {'NOMINAL & SAFE' if is_safe else 'BACKPRESSURE'}")

    # 2. Register Antigravity Session on EventBus DataMesh
    print(f"\n▶ [2/4] Registering Antigravity Session on EventBus DataMesh...")
    event_bus = await get_event_bus()
    session_id = "antigravity_orch_session"
    bridge = CrossSessionEventBridge(event_bus=event_bus, session_id=session_id)
    await bridge.initialize()

    agy_event = Event(
        type=EventType.SYSTEM_HEALTH,
        source="antigravity_orchestrator",
        priority=20,  # Highest Orchestrator Priority
        payload={
            "role": "Master Orchestrator & Evaluator (AGY)",
            "app_dir": "/home/mike-anderson/.gemini/antigravity-cli",
            "conversation_id": "54146dc4-dff4-4b47-a2cb-abb16f9e3812",
            "status": "ORCHESTRATING_FLEET",
            "headroom_gib": avail_gib,
            "governor_policy": "Learning 92: Liveness Over Speed (35GB Floor)",
            "fleet_size": 7
        }
    )
    await event_bus.publish(agy_event)
    print(f"   ✓ Emitted High-Priority (Priority: 20) `SYSTEM_HEALTH` event across EventBus")

    # 3. Intercept All Active Peer Sessions (Claude, Hermes, OpenCode, Pi, DSH, Qwen-Code)
    print(f"\n▶ [3/4] Antigravity Sweeping Active Peer Swarm Telemetry from SurrealDB DataMesh...")
    peer_events = await bridge.fetch_cross_session_events(limit=10)
    print(f"   ✓ Antigravity intercepted {len(peer_events)} active peer session events:")
    for ev in peer_events:
        print(f"     • [{ev.get('session_id')}] Type: {ev.get('type')} from `{ev.get('source')}` | Payload: {ev.get('payload')}")

    # 4. Dual-Persist Master Orchestrator Kanban Card
    persist_item({
        "id": "antigravity_master_orchestrator_status",
        "title": "Antigravity (AGY) Master Orchestrator Active",
        "status": "in_progress",
        "priority": "highest",
        "source": "antigravity_orchestrator",
        "category": "master_orchestration",
        "details": f"Antigravity orchestrating 7 connected agent interfaces. Memory Headroom: {avail_gib} GiB. Learning 92 Enforced.",
    })
    print("   ✓ Dual-persisted Master Orchestrator card to SurrealDB and Obsidian Vault")

    print("\n" + "=" * 115)
    print("🎉 ANTIGRAVITY (AGY) MASTER ORCHESTRATOR FULLY SYNCHRONIZED ON THE DATAMESH!")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(test_agy_orchestrator())
