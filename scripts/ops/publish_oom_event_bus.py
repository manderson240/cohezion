#!/usr/bin/env python3
"""Publish calibrated OOM recovery event with exact EventBus signature."""

from __future__ import annotations

import asyncio

from cohezion.core.event_bus import Event, EventBus


async def main() -> None:
    bus = EventBus()
    event = Event.agent_complete(
        agent_name="antigravity-oom-investigator",
        duration_ms=45200.0,
        result={
            "finding": "OOM Recovery Post-Mortem completed. Identified concurrent headless Chromium memory leak + uncollected dense 3D NumPy matrices during GPU TRELLIS diffusion.",
            "severity": "critical",
            "category": "system_reliability",
            "available_ram_gib": 76.0,
            "status": "remediated"
        }
    )
    await bus.publish(event)
    print("✓ EventBus Event published cleanly with correct schema.")

if __name__ == "__main__":
    asyncio.run(main())
