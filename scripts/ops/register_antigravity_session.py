#!/usr/bin/env python3
"""Antigravity Orchestrator EventBus Registration & Resource Coordination Bridge.

Registers the current interactive Antigravity session with the Cohezion EventBus,
publishes heartbeat and coordination events to SurrealDB `event_log`, and syncs
with active daemons and peer sessions.
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.reliability.oom_guard import OOMGuard


async def register_session_with_eventbus():
    print("\n" + "=" * 90)
    print("      🛰️ REGISTERING ANTIGRAVITY ORCHESTRATOR WITH LIVE EVENTBUS & SURREALDB")
    print("=" * 90)

    bus = await get_event_bus()
    session_id = "antigravity-master-54146dc4"
    bridge = CrossSessionEventBridge(event_bus=bus, session_id=session_id)
    await bridge.initialize()

    mem = OOMGuard.get_memory_state()

    print(f"Session ID: {session_id}")
    print(
        f"Memory Available: {mem.available_gb:.1f} GiB / {mem.total_gb:.1f} GiB (Safe={mem.is_safe})"
    )

    # 1. Publish Session Registration Event
    reg_event = Event(
        type=EventType.AGENT_START,
        source="orchestrator.antigravity",
        payload={
            "role": "Master Orchestrator & Evaluator",
            "tier_routing": "Local-First Tri-Tier",
            "active_accelerators": ["AMD XDNA2 NPU", "Radeon 8060S iGPU", "Ryzen CPU"],
            "memory_available_gb": round(mem.available_gb, 2),
            "coordination_status": "SYNCHRONIZED",
            "action": "SESSION_REGISTERED",
        },
    )
    await bus.publish(reg_event)
    print("✓ Published `SESSION_REGISTERED` event to EventBus and SurrealDB `event_log`.")

    # 2. Publish System Resource Allocation Lease Event
    lease_event = Event(
        type=EventType.SYSTEM_HEALTH,
        source="orchestrator.antigravity",
        payload={
            "npu_claim": "embed-gemma-300m-FLM / llama3.2-1b-FLM (Non-exclusive)",
            "igpu_claim": "Qwen3.8-27B-GGUF-Q5_K_M (Active Lane)",
            "concurrency_discipline": "Quarter-on-the-string / FleetLock active",
            "max_vram_saturation": 0.90,
            "status": "GRANTED",
            "action": "RESOURCE_COORDINATION_LEASE",
        },
    )
    await bus.publish(lease_event)
    print("✓ Published `RESOURCE_COORDINATION_LEASE` event.")

    # Allow event bridge to process and persist
    await asyncio.sleep(0.5)

    # 3. Verify delivery metrics
    metrics = bus.get_metrics()
    print(
        f"\nLive EventBus Metrics: Published={metrics.get('published')}, Delivered={metrics.get('delivered')}, Errors={metrics.get('errors')}"
    )

    await bus.stop()
    print("=" * 90 + "\n")


if __name__ == "__main__":
    asyncio.run(register_session_with_eventbus())
