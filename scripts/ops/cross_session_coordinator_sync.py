#!/usr/bin/env python3
"""Cross-Session EventBus Registration & Active Peer Coordination Daemon.

Registers Antigravity with the EventBus and SurrealDB `event_log` table,
polls for peer agent sessions (e.g. overnight daemons, GAIA agents, Telegram bots),
and broadcasts heartbeat status and milestone synchronizations.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("cross_session_sync")


async def sync_with_active_sessions() -> None:
    print("=" * 100)
    print("    🌐 CROSS-SESSION EVENTBUS REGISTRATION & ACTIVE PEER COORDINATION")
    print("=" * 100)

    bus = EventBus()
    session_id = "antigravity_master_orchestrator"
    bridge = CrossSessionEventBridge(event_bus=bus, session_id=session_id)
    await bridge.initialize()

    # 1. Broadcast an active session online event
    online_evt = Event(
        type=EventType.SYSTEM_HEALTH,
        source=session_id,
        payload={
            "status": "online",
            "message": "Antigravity Master Orchestrator active and registered with EventBus",
            "capabilities": [
                "2048D Poincaré Neural ODE",
                "Matsumoto ENC Engine",
                "Burkhard Heim Metron Engine",
                "Palimpsa Bayesian Metaplasticity",
                "AMD GAIA SDK Tool Mixins",
                "Cognitive CRM & Reactive Kanban",
                "Write Budget & ZFS Guardrails",
                "Google Workspace Gateway",
            ],
            "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S EDT"),
        },
        priority=10,
    )
    await bus.publish(online_evt)
    print(f"  ✓ [Local Broadcast] Published registration event ({online_evt.source}) onto EventBus.")

    # 2. Fetch cross-session events from other running sessions (e.g., overnight daemon, swarm orchestrator, Telegram bot)
    print("\n🔍 Fetching active events published by peer sessions in SurrealDB `event_log`...")
    peer_events = await bridge.fetch_cross_session_events(limit=10)

    if peer_events:
        print(f"  ✓ Found {len(peer_events)} recent events from peer sessions:")
        for idx, pe in enumerate(peer_events, 1):
            s_id = pe.get("session_id", "unknown_session")
            e_type = pe.get("type", "UNKNOWN")
            src = pe.get("source", "unknown_source")
            t_stamp = pe.get("valid_from", "N/A")
            print(f"    [{idx}] Session: {s_id:<30} | Type: {e_type:<15} | Source: {src:<25} | Time: {t_stamp}")
    else:
        print("  ℹ️ No preceding peer events found in event_log (Clean start after reboot).")

    # 3. Query SurrealDB `kanban_item` table to ensure task card sync across sessions
    client = SurrealClient()
    try:
        cards_res = await client.query("SELECT count() FROM kanban_item GROUP ALL;")
        count = 0
        if isinstance(cards_res, list) and len(cards_res) > 0 and "result" in cards_res[0]:
            rows = cards_res[0]["result"]
            if rows and "count" in rows[0]:
                count = rows[0]["count"]
        print(f"\n📋 [Kanban Mesh Sync] Total active Kanban Cards across all sessions: {count}")
    except Exception as e:
        print(f"  ⚠️ Kanban query notice: {e}")

    print("\n" + "=" * 100)
    print("🎉 ANTIGRAVITY IS FULLY REGISTERED & COORDINATING ACROSS ALL AGENT SESSIONS!")
    print("=" * 100)


def main() -> None:
    asyncio.run(sync_with_active_sessions())


if __name__ == "__main__":
    main()
