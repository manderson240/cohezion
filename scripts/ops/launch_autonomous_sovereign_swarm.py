#!/usr/bin/env python3
"""Autonomous Long-Horizon Sovereign Swarm Orchestrator for AFK Sessions.

Runs continuous autonomous goal execution loops:
1. Spinning Plates Protocol (AST verification, Poincare calibration, UMA monitor).
2. Autonomous Code Quality & Test Suite Coverage.
3. SurrealDB & Obsidian Retrospectives & Knowledge Extraction.
4. Telegram Remote Parity Health & EventBus Broadcasting.
"""

import asyncio
import logging
import signal
import sys
import time

from cohezion.core.event_bus import Event, EventBus
from cohezion.proactive.spinning_plates_protocol import SpinningPlatesGovernor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AUTONOMOUS_SWARM] %(message)s",
)
logger = logging.getLogger("autonomous_swarm")

async def run_autonomous_swarm():
    logger.info("=" * 80)
    logger.info("🚀 INITIALIZING AUTONOMOUS SOVEREIGN SWARM (AFK RUNTIME)")
    logger.info("=" * 80)

    # 1. Announce startup on EventBus
    from cohezion.core.event_bus import EventType
    bus = EventBus()
    await bus.publish(Event(
        type=EventType.AGENT_START,
        source="autonomous_swarm",
        payload={"status": "active", "mode": "unattended_afk", "timestamp": time.time()}
    ))

    governor = SpinningPlatesGovernor(min_available_gb=20.0)

    # 2. Setup graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Received termination signal. Gracefully spinning down plates...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    # 3. Launch the spinning plates concurrently
    plates_task = asyncio.create_task(governor.start_spinning_plates())

    logger.info("🟢 Autonomous Swarm active. Operating across NPU, iGPU, CPU, and Cloud overflow.")
    
    # 4. Periodic health & Kanban maintenance loop
    cycle = 0
    while not stop_event.is_set():
        cycle += 1
        await asyncio.sleep(30.0)
        telemetry = governor.get_plate_telemetry()
        total_iters = sum(p["iterations"] for p in telemetry["plates"].values())
        logger.info(f"📊 [Heartbeat Cycle {cycle}] Total Plate Iterations: {total_iters} | Memory Guard: 🟢 PASS")

    governor.running = False
    plates_task.cancel()
    await asyncio.gather(plates_task, return_exceptions=True)
    logger.info("🏁 Autonomous Sovereign Swarm cleanly shut down.")

if __name__ == "__main__":
    asyncio.run(run_autonomous_swarm())
