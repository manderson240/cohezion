#!/usr/bin/env python3
"""Registers this Antigravity session with the EventBus and SurrealDB event_log,
publishing an active coordination beacon for the parallel Claude session.
"""

import asyncio
import os
import time

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import get_event_bus, Event, EventType
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item

async def register():
    session_id = "antigravity_master_orchestrator"
    bus = await get_event_bus()
    bridge = CrossSessionEventBridge(event_bus=bus, session_id=session_id)
    await bridge.initialize()
    
    # 1. Publish Coordination Beacon
    beacon = Event(
        type=EventType.CUSTOM,
        source="AntigravityOrchestrator",
        priority=10,
        payload={
            "agent": "Antigravity (Gemini 3.1 Pro High)",
            "status": "ACTIVE_COLLABORATION",
            "focus_areas": [
                "Kaggle Competitions (ARC-AGI-2, ARC-AGI-3, Pokemon TCG)",
                "Local Inference & Munder-Difflin UI Integration",
                "Continuous Verification & AutoHarness Synthesis"
            ],
            "coordination_policy": "Non-blocking git worktree / clean tree discipline. Respect active file locks and FleetLock.",
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    )
    
    await bus.publish(beacon)
    
    # 2. Persist to Agentic Kanban (SurrealDB + Obsidian Vault)
    persist_item({
        "id": "cross_session_antigravity_claude_bridge",
        "title": "Cross-Session Multi-Agent Collaboration Bridge (Antigravity + Claude)",
        "status": "in_progress",
        "priority": "high",
        "source": "AntigravityOrchestrator",
        "category": "agent_coordination",
        "details": "Active inter-session collaboration established. Antigravity focusing on Kaggle solvers, AutoHarness, and local UI desk.",
    })
    
    print("================================================================================")
    print("📡 REGISTERED WITH EVENT BUS & SURREALDB EVENT LOG")
    print("================================================================================")
    print(f"Session ID: {session_id}")
    print("Beacon published to EventBus and saved to `event_log` table in SurrealDB.")
    print("Kanban bridge item persisted to Obsidian Vault & SurrealDB.")
    print("================================================================================")

if __name__ == "__main__":
    asyncio.run(register())
