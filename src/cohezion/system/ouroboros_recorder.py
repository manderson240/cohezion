"""
Ouroboros Sensor Fusion Recorder.

Acts as a 'Flight Recorder' for the Cohezion system, fusing:
1. Hardware Vitals (CPU, RAM, VRAM, GTT) from ResourceMonitor.
2. Software Health (Git Entropy, Bloat) from GitHealth.
3. System Dilation Factor.
4. Universe Trajectory Tracking (12D/512D manifold).
5. Self-Improvement via Evolution Orchestrator.

Persists data to 'system_pulse' table in SurrealDB every interval.
Integrated with Universe v2 for compound engineering.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from cohezion.db.admin import DBAdmin
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.swarm.git_health import get_repo_bloat

logger = logging.getLogger(__name__)


class OuroborosRecorder:
    """
    Ouroboros Sensor Fusion Recorder with Universe v2 Integration.

    Features:
    - Hardware/software sensor fusion
    - Universe trajectory tracking
    - Automatic self-improvement via Evolution Orchestrator
    - XP rewards for system improvements
    """

    def __init__(self, interval_seconds: int = 10):
        self.interval = interval_seconds
        self.dba = DBAdmin()
        self.monitor = get_resource_monitor()
        self._running = False
        self._task = None

        # Universe v2 integration
        self._universe_journey: Optional[Any] = None
        self._universe_engine = None
        self._rewards = None
        self._evolution = None

    async def _ensure_universe(self):
        """Lazy initialization of Universe v2 components."""
        if self._universe_engine is None:
            from cohezion.universe.engine import UniverseSimulationEngine
            from cohezion.rewards.system import RewardSystem
            from cohezion.meta.evolution import EvolutionOrchestrator

            self._universe_engine = UniverseSimulationEngine()
            self._rewards = RewardSystem()
            self._evolution = EvolutionOrchestrator(auto_deploy=False)

            self._universe_journey = await self._universe_engine.start_journey(
                agent_name="OuroborosRecorder",
                intent="System monitoring, self-improvement, and evolution",
            )
            logger.info("🌌 Ouroboros joined the Universe")

    async def start(self):
        """Start the background recording loop with Universe v2 tracking."""
        if self._running:
            return

        await self._ensure_universe()

        await self.dba.connect()
        self._running = True
        self._task = asyncio.create_task(self._record_loop())
        logger.info("🔴 Ouroboros Recorder STARTED with Universe v2")

    async def stop(self):
        """Stop the recorder and precipitate final state."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._universe_journey and self._universe_engine:
            await self._universe_engine.precipitate_reality(
                journey=self._universe_journey,
                outputs={
                    "status": "stopped",
                    "cycles": getattr(self, "_reflex_counter", 0),
                },
                phi_score=0.75,
            )

        logger.info("⚫ Ouroboros Recorder STOPPED")

    async def _record_loop(self):
        """Main recording loop with Universe tracking."""
        cycle_count = 0

        while self._running:
            try:
                start_time = time.perf_counter()

                cycle_count += 1

                await self._ensure_universe()

                hw_vitals = self.monitor.get_vitals()
                dilation = self.monitor.get_dilation_factor()

                logger.info("Reading Git Health...")
                try:
                    loop = asyncio.get_running_loop()
                    sw_vitals = await asyncio.wait_for(
                        loop.run_in_executor(None, get_repo_bloat), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Git Health Sensor timed out")
                    sw_vitals = {"error": "timeout"}

                pulse_packet = {
                    "hardware": hw_vitals,
                    "software": sw_vitals,
                    "dilation_factor": dilation,
                    "cycle": cycle_count,
                }

                res = await self.dba.client.create("system_pulse", pulse_packet)
                logger.info(f"💾 Pulse Saved (cycle {cycle_count})")

                await self._universe_engine.evolve_trajectory(
                    journey=self._universe_journey,
                    action="pulse_recorded",
                    result=f"hw_keys={len(hw_vitals)}, sw_keys={len(sw_vitals)}",
                    phi_score=0.6 + (0.1 if dilation < 1.5 else 0),
                )

                elapsed = time.perf_counter() - start_time
                await asyncio.sleep(max(1.0, self.interval - elapsed))

            except Exception as e:
                logger.error(f"Ouroboros Recording Failed: {e}")
                await asyncio.sleep(self.interval)

            await self._reflex_cycle(cycle_count)

    async def _reflex_cycle(self, cycle_count: int):
        """Execute reflex cycle for self-improvement."""
        if cycle_count % 30 != 0:
            return

        logger.info("🧠 Triggering Reflex Cycle...")
        try:
            self._evolution.analyze_code()
            suggestions = self._evolution.generate_suggestions()

            auto_deploy = [s for s in suggestions if s.action == "auto_deploy"]
            review = [s for s in suggestions if s.action == "review_required"]

            await self._universe_engine.evolve_trajectory(
                journey=self._universe_journey,
                action="reflex_cycle",
                result=f"patterns={len(suggestions)}, auto={len(auto_deploy)}, review={len(review)}",
                phi_score=0.7,
            )

            if auto_deploy:
                logger.info(f"   📝 {len(auto_deploy)} auto-deploy suggestions")
                self._rewards.award_xp(
                    agent_id="OuroborosRecorder",
                    amount=len(auto_deploy) * 5,
                    reason=f"Detected {len(auto_deploy)} improvement patterns",
                )

            logger.info(f"   🔍 {len(review)} patterns need review")

        except Exception as e:
            logger.error(f"Reflex cycle failed: {e}")

    async def get_status(self, detailed: bool = False) -> dict[str, Any]:
        """Get current system status."""
        await self._ensure_universe()

        status = {
            "running": self._running,
            "interval_seconds": self.interval,
            "universe_journey": self._universe_journey.id
            if self._universe_journey
            else None,
        }

        if detailed:
            status["hardware_vitals"] = self.monitor.get_vitals()
            status["dilation_factor"] = self.monitor.get_dilation_factor()
            status["rewards"] = (
                self._rewards.get_status("OuroborosRecorder") if self._rewards else None
            )

        return status


async def main():
    """Standalone test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Ouroboros System Recorder")
    parser.add_argument("--interval", type=int, default=10, help="Recording interval")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    recorder = OuroborosRecorder(interval_seconds=args.interval)

    if args.status:
        status = await recorder.get_status(detailed=True)
        import json

        print(json.dumps(status, indent=2, default=str))
        return

    await recorder.start()
    await asyncio.sleep(30)
    await recorder.stop()


if __name__ == "__main__":
    asyncio.run(main())
