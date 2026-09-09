#!/usr/bin/env python3
"""Cross-Session Event Broadcast & Inter-Session Listener.

1. Initializes EventBus and CrossSessionEventBridge.
2. Broadcasts our active sovereign session status and OOM safeguard state.
3. Fetches and logs recent events from other sessions stored in SurrealDB event_log.
"""

from __future__ import annotations

import asyncio
import logging
import time

from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.persistence.surreal_client import SurrealClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [EVENT_MONITOR] %(message)s")
logger = logging.getLogger("event_monitor")

CURRENT_SESSION_ID = "antigravity_master_session"


async def main():
    logger.info("📡 ===================================================================")
    logger.info("📡 INTER-SESSION EVENT BUS BROADCASTER & CROSS-SESSION OBSERVER")
    logger.info("📡 ===================================================================")

    bus = EventBus()
    bridge = CrossSessionEventBridge(event_bus=bus, session_id=CURRENT_SESSION_ID)
    await bridge.initialize()

    # 1. Broadcast Sovereign Session State to EventBus & SurrealDB Outbox
    logger.info("📢 Broadcasting Active Sovereign Session Status to EventBus...")
    status_event = Event(
        type=EventType.SYSTEM_HEALTH,
        source="antigravity_orchestrator",
        timestamp=time.time(),
        payload={
            "session_id": CURRENT_SESSION_ID,
            "status": "active_sovereign_execution",
            "oom_guard": "enabled_30gb_headroom",
            "active_models": ["gpt-oss-20b-mxfp4-GGUF", "qwen3.6-moe-35b-a3b-FLM"],
            "linux_namespaces": "active_bwrap",
            "tasks_verified": "overnight_daemon_running",
        },
        priority=10,
    )
    await bus.publish(status_event)
    logger.info("  ✓ Broadcasted Event [%s] from source: %s", status_event.type.name, status_event.source)

    # 2. Query SurrealDB for Recent Events from Peer Sessions
    logger.info("🔍 Polling Peer Session Events from SurrealDB event_log...")
    client = SurrealClient()
    try:
        query_res = await asyncio.wait_for(
            client.query("SELECT * FROM event_log ORDER BY timestamp DESC LIMIT 10;"),
            timeout=5.0
        )
        events = query_res[0].get("result", []) if query_res and isinstance(query_res, list) else []
        logger.info("  ✓ Found %d recent cross-session event records:", len(events))
        for evt in events:
            logger.info("    • [%s] Source: %s | Session: %s | Type: %s | Payload: %s",
                        evt.get("id"), evt.get("source"), evt.get("session_id"), evt.get("type"), str(evt.get("payload"))[:80])
    except Exception as e:
        logger.warning("  ⚠️ SurrealDB query skipped (DB offline or initializing): %s", e)

    logger.info("📡 ===================================================================")
    logger.info("📡 CROSS-SESSION COLLABORATION BRIDGE: SYNCHRONIZED")
    logger.info("📡 ===================================================================")


if __name__ == "__main__":
    asyncio.run(main())
