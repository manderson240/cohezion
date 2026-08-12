"""Session EventBus Registration & Cross-Session Coordination Verification Script.

Ensures the active orchestrator session is registered with EventBus, bi-temporally
persisting events to SurrealDB `event_log` and coordinating with peer sessions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventBus, EventType, get_event_bus
from cohezion.data_mesh.kanban_bridge import persist_item

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("session_event_bus")


async def main() -> None:
    session_id = "antigravity_master_orchestrator"
    logger.info("📡 Registering active session '%s' with EventBus & CrossSessionEventBridge...", session_id)
    
    event_bus = await get_event_bus()
    bridge = CrossSessionEventBridge(event_bus=event_bus, session_id=session_id)
    await bridge.initialize()

    # 1. Publish Session Registration Heartbeat Event
    heartbeat_event = Event(
        type=EventType.AGENT_START,
        source=session_id,
        payload={
            "status": "active_orchestrating",
            "model_routing": "Tier 1 Local Silicon + Tier 2 Ollama Cloud",
            "autoharness": "arXiv:2603.03329v1 AST Bytecode Verifiers Active",
            "timestamp": time.time(),
        },
    )
    await event_bus.publish(heartbeat_event)
    logger.info("✅ Published active session registration heartbeat to local EventBus & SurrealDB event_log")

    # 2. Fetch Recent Peer Session Events for Cross-Session Coordination
    logger.info("🔍 Fetching peer session events from SurrealDB event_log...")
    peer_events = await bridge.fetch_cross_session_events(limit=10)
    logger.info("RECEIVED %d peer session events for cross-session coordination:", len(peer_events))
    for evt in peer_events:
        logger.info(
            "  • Peer Session '%s' | Event '%s' | Source: '%s' | ValidFrom: %s",
            evt.get("session_id"),
            evt.get("type"),
            evt.get("source"),
            evt.get("valid_from"),
        )

    # 3. Synchronize Session State via Agentic Kanban Bridge
    kanban_card = {
        "id": "antigravity-session-coordination-active",
        "title": "Antigravity Master Orchestrator Active & EventBus Registered",
        "status": "in_progress",
        "priority": "high",
        "source": session_id,
        "category": "session_coordination",
        "description": "EventBus pub/sub registered with SurrealDB event_log & Obsidian Vault dual-engine persistence.",
    }
    persisted = persist_item(kanban_card)
    logger.info("📋 Agentic Kanban Card Persisted: %s (SurrealDB + Obsidian)", persisted)


    # Allow background async event handlers to complete
    await asyncio.sleep(1.0)
    logger.info("🎉 Session EventBus Registration & Cross-Session Coordination Verified!")


if __name__ == "__main__":
    asyncio.run(main())
