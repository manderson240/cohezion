#!/usr/bin/env python3
"""Register an agent session with the EventBus + CrossSessionEventBridge.

Usage:
    PYTHONPATH=src uv run python scripts/ops/register_session.py \
        --session-id "gic-latency-tiering-20260815" \
        --goal "Latency-aware GIC tier selection + CI repair"

Publishes:
  1. AGENT_START event on the local EventBus
  2. Persists the event to SurrealDB event_log via CrossSessionEventBridge
  3. Creates a kanban card via kanban_bridge.persist_item()

This is the durable registration point that makes the session visible to
other agents, the Obsidian vault, and SurrealDB dashboards.
"""

from __future__ import annotations

import argparse
import asyncio
import time

from cohezion.core.event_bus import Event, get_event_bus
from cohezion.data_mesh.kanban_bridge import persist_item


async def register(session_id: str, goal: str) -> None:
    bus = await get_event_bus()
    await bus.publish(
        Event.agent_start(
            agent_name=session_id,
            model="glm-5.2:cloud",
            goal=goal,
        )
    )
    persist_item(
        {
            "id": f"session-{session_id}",
            "title": goal,
            "status": "in_progress",
            "priority": "high",
            "source": f"session/{session_id}",
            "category": "improvement",
            "description": goal,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    metrics = bus.get_metrics()
    print(f"EventBus: published={metrics['published']}, handlers={metrics['handlers']}")
    print(f"Kanban: persisted to SurrealDB + Obsidian")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--goal", required=True)
    args = parser.parse_args()
    asyncio.run(register(args.session_id, args.goal))


if __name__ == "__main__":
    main()
