#!/usr/bin/env python3
"""
Fractal Nexus Convergence Mission (15H)
=======================================
A long-horizon autonomous research sprint focusing on HIHO stability,
mechanistic interpretability, and multi-modal resonance.

Features:
- Resource-Aware Scaling (Dynamic Throttle)
- Memory Recovery Protocol (MRP) Integration
- SurrealDB Persistent Pulsing
- Mechanistic Interpretability reports (DeepSeek-R1)
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from cohezion.mcp.email_notifier import EmailNotifier
from cohezion.monitoring.ratchet_monitor import RatchetMonitor
from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.journey_tracker import (
    AgentType,
    JourneyMetrics,
    get_journey_tracker,
)

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)

# Core Cohezion Imports
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine
from cohezion.swarm.swarm_types import SwarmConfig


# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FractalNexus")

# Constants
MISSION_DURATION_HOURS = 15
PULSE_INTERVAL_MINUTES = 30
REPORT_INTERVAL_HOURS = 3
DEFAULT_NUM_ROUNDS = 1_000_000
MAX_NUM_ROUNDS = 5_000_000
MIN_NUM_ROUNDS = 100_000


class FractalNexusMission:
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=MISSION_DURATION_HOURS)
        self.ratchet = RatchetMonitor(email_to="manderson240@gmail.com")
        self.notifier = EmailNotifier()
        self.db = SurrealClient()
        self.engine = HihoVectorEngine(num_rounds=DEFAULT_NUM_ROUNDS)
        self.config = SwarmConfig(mrp_sync=True)
        self.tracker = get_journey_tracker()

        # Scaling State
        self.num_rounds = DEFAULT_NUM_ROUNDS
        self.batch_count = 0
        self.total_cycles = 0
        self.stability_history = []
        self.checkpoint_path = Path("mission_checkpoint.json")
        self.cpu_freq_base = psutil.cpu_freq().current if psutil.cpu_freq() else 1.0

        logger.info(f"❄️ Fractal Nexus Mission Initialized. Duration: {MISSION_DURATION_HOURS}H")
        logger.info(f"   Target End: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    async def initialize(self):
        """Perform MRP Wake-Up and DB Connection."""
        logger.info("Initializing Mission Infrastructure...")
        try:
            await self.db.connect()
            await self.db.setup_schema()
            logger.info("✓ SurrealDB Connected")
        except Exception as e:
            logger.error(f"❌ SurrealDB connection failed: {e}")

        # Register the mission start using UniverseNode
        status_node = UniverseNode(
            id="mission_status_fractal_nexus",
            content="Fractal Nexus Mission Status",
            node_type="mission_status",
            metadata={
                "mission": "Fractal Nexus",
                "start_time": self.start_time.isoformat(),
                "status": "in_progress",
                "initial_rounds": self.num_rounds,
            },
        )
        await self.db.store_node(status_node)

        # Load Checkpoint if exists
        await self._load_checkpoint()

    async def _adjust_dynamics(self):
        """Dynamic Scaling: Adjust num_rounds based on system resources."""
        vitals = self.ratchet.check_vitals()

        # INCREASE DYNAMICS: If system is healthy, be much more aggressive
        # Thresholds relaxed for 128GB Framework 16
        if vitals.ram_percent < 65 and vitals.cpu_percent < 60 and self.num_rounds < MAX_NUM_ROUNDS:
            self.num_rounds = min(MAX_NUM_ROUNDS, int(self.num_rounds * 1.2))  # Reduced from 1.5x
            logger.info(f"🚀 High inference headroom. Scaling UP dynamics: {self.num_rounds:,} rounds")
        # THROTTLE: Only if approaching critical
        elif vitals.needs_throttle():
            self.num_rounds = max(MIN_NUM_ROUNDS, int(self.num_rounds * 0.5))
            logger.warning(f"⚠️ System pressure detected. Scaling DOWN dynamics: {self.num_rounds:,} rounds")

        self.engine.num_rounds = self.num_rounds

    async def run_iteration(self):
        """Execute one HIHO simulation cycle and interpret results."""
        self.batch_count += 1
        logger.info(f"Iteration {self.batch_count}: Simulating {self.num_rounds:,} rounds...")

        # Start Journey Tracking for this iteration
        self.tracker.start_journey(f"Fractal Nexus Iteration {self.batch_count}")
        start_time = time.perf_counter()

        # 1. Physics Simulation
        results = await asyncio.to_thread(self.engine.run_simulation)
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Calculate Computational Relativity
        current_cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else self.cpu_freq_base
        relativity_factor = current_cpu_freq / self.cpu_freq_base
        logic_velocity = self.num_rounds / (duration_ms / 1000)

        metrics = JourneyMetrics(
            context_utilization=0.9,  # Simulated for now
            latent_coherence=results["mean_stability"],
            capability_delta=results["mean_stability"] - (self.stability_history[-1] if self.stability_history else 0),
            latency_per_token_ms=duration_ms / self.num_rounds * 1000,
            safety_alignment_score=0.98,
            computational_relativity_factor=relativity_factor,
        )

        # Record the Physics Step in the Journey
        self.tracker.record_step(
            agent_type=AgentType.ANALYST,
            agent_name="HihoVectorEngine",
            perspective="PHYSICAL",
            input_text=f"Params: rounds={self.num_rounds}",
            output_text=f"Stability: {results['mean_stability']:.4f}, Velocity: {logic_velocity:.0f} Hz",
            physics_state={
                "coherence": results["mean_stability"],
                "stability": results["mean_stability"],
                "novelty": float(results["max_reality"]),
                "relativity": relativity_factor,
            },
            duration_ms=duration_ms,
            confidence=results["mean_stability"],
            metrics=metrics,
        )

        self.total_cycles += self.num_rounds
        self.stability_history.append(results["mean_stability"])

        # 2. Mechanistic Interpretability (if stability breakthrough detected)
        if results["mean_stability"] > 0.96:
            interpretation = await self._run_interpretability_report(results)
            # Record the Interpretability Step
            self.tracker.record_step(
                agent_type=AgentType.CRITIC,
                agent_name="DeepSeek-R1",
                perspective="INTERPRETABILITY",
                input_text="Explain breakthrough stability.",
                output_text=interpretation[:200] + "..." if interpretation else "None",
                physics_state={"coherence": results["mean_stability"]},
                duration_ms=5000,  # Estimated
                confidence=results["mean_stability"],
            )

        # 3. Store Results to SurrealDB
        await self._store_iteration_results(results)

        # 4. Periodic Pulse
        if self.batch_count % 5 == 0:
            await self._emit_mission_pulse(results)

        # End Journey and Persist to SurrealDB
        await self.tracker.end_journey(
            final_response=f"Stability Convergence: {results['mean_stability']:.4f}",
            final_confidence=results["mean_stability"],
            aggregate_metrics=metrics,
        )

        # 5. Checkpoint
        await self._save_checkpoint()

    async def _run_interpretability_report(self, results):
        """Query DeepSeek-R1 for 'Black Box' transparency."""
        logger.info("✨ Stability Breakthrough! Reporting for interpretability...")

        # Sample top bright spots for the prompt
        samples = results["bright_spot_states"][:3].tolist()

        # Calculate resonance for the first sample to show in report
        resonance = self._calculate_resonance(results["mean_stability"])

        prompt = f"""MECHANISTIC INTERPRETABILITY REPORT (FRACTAL NEXUS):
Stability achieved: {results["mean_stability"]:.4f}
Resonance Frequency: {resonance:.2f} Hz
Bright Spots: {results["bright_spot_count"]:,}
Sample Coordinates (12D): {samples}

Explain the emergent resonance patterns in the FLUME manifold.
Why is this specific 12D coordinate stable?
Address the "Black Box" concern: what is the underlying physics logic of this convergence?
"""
        try:
            # Using deepseek-r1:70b as requested for architecture/thinking
            agent = BaseAgent(model_name="deepseek-r1:70b", config=self.config)
            interpretation = await agent._call_ollama(prompt)
            await agent.close()

            # Store interpretation
            await self.db.store_node(
                "interpretability_reports",
                {
                    "iteration": self.batch_count,
                    "stability": results["mean_stability"],
                    "resonance_hz": resonance,
                    "content": interpretation,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            logger.info("✓ Interpretability report persisted.")
            return interpretation
        except Exception as e:
            logger.error(f"Failed interpretability report: {e}")
            return None

    def _calculate_resonance(self, stability: float) -> float:
        """
        Map stability to audio frequencies (Resonance Mapping).
        Base: 432 Hz (Universal resonance)
        Distance from 1.0 stability (which is 0.5 coherence) shifts frequency.
        """
        # Distance from perfect stability (1.0)
        dist = 1.0 - stability
        # Frequency shifts between 432Hz (Stable) and 864Hz (Unstable)
        freq = 432.0 + (dist * 432.0)
        return freq

    async def _store_iteration_results(self, results):
        """Persist simulation summary to SurrealDB."""
        resonance = self._calculate_resonance(results["mean_stability"])
        try:
            node = UniverseNode(
                id=f"sim_{int(time.time())}_{self.batch_count}",
                content=f"Fractal Nexus Iteration {self.batch_count}",
                node_type="simulation_step",
                physics_state=PhysicsState(
                    time=float(time.time()),
                    coherence=results["mean_stability"],
                    stability=results["mean_stability"],
                    novelty=float(results["max_reality"]),
                ),
                metadata={
                    "num_rounds": results["num_rounds"],
                    "bright_spots": results["bright_spot_count"],
                    "duration": results["duration"],
                    "resonance_hz": resonance,
                },
            )
            await self.db.store_node(node)
        except Exception as e:
            logger.error(f"Failed to store iteration results: {e}")

    async def _emit_mission_pulse(self, results):
        """Send MISSION_PULSE to SurrealDB for session anchoring."""
        try:
            pulse = {
                "mission": "Fractal Nexus",
                "timestamp": datetime.now().isoformat(),
                "iteration": self.batch_count,
                "total_cycles": self.total_cycles,
                "current_stability": results["mean_stability"],
                "resource_rounds": self.num_rounds,
                "vitals": self.ratchet.check_vitals().__dict__,
            }
            # Use SQL parameters for safer and correct syntax
            await self.db.query("CREATE mission_pulse CONTENT $pulse", {"pulse": pulse})
            logger.debug("🌐 MISSION_PULSE emitted.")
        except Exception as e:
            logger.error(f"Failed mission pulse: {e}")

    async def run(self):
        """Main Loop."""
        await self.initialize()

        logger.info("Mission Started. Scaling dynamics enabled.")

        while datetime.now() < self.end_time:
            try:
                # 1. Scaling & Pressure Check
                from cohezion.reliability.monitor import get_resource_monitor

                monitor = get_resource_monitor()
                if monitor.critical_pressure:
                    logger.error("🛑 EMERGENCY SYSTEM PRESSURE DETECTED. Pausing iteration for cooldown...")
                    await asyncio.sleep(120)  # 2 minute hard pause
                    continue

                await self._adjust_dynamics()

                # 2. Work
                await self.run_iteration()

                # 3. Throttle/Cooling
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Iterative failure: {e}")
                await self._save_checkpoint()  # Save what we have
                await asyncio.sleep(60)  # Cooldown on failure

        logger.info("Mission Completion Threshold Reached.")
        await self._finalize_mission()

    async def _finalize_mission(self):
        """Finalize mission and trigger reporting."""
        logger.info("Finalizing Fractal Nexus Mission...")
        # Mark mission as complete in DB
        await self.db.query(
            "UPDATE mission_status SET status = 'completed', end_time = '"
            + datetime.now().isoformat()
            + "' WHERE mission = 'Fractal Nexus'"
        )

        # Trigger the Finalizer Script
        import subprocess

        subprocess.Popen(["uv", "run", "python3", "scripts/mission_finalizer.py"])
        subprocess.Popen(["uv", "run", "python3", "scripts/mission_finalizer.py"])
        logger.info("🚀 mission_finalizer.py triggered.")
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()

    async def _save_checkpoint(self):
        """Save mission state to SurrealDB and local file."""
        checkpoint = {
            "batch_count": self.batch_count,
            "total_cycles": self.total_cycles,
            "num_rounds": self.num_rounds,
            "stability_history": self.stability_history[-100:],  # keep last 100
            "timestamp": datetime.now().isoformat(),
        }
        try:
            # Save to Local
            with open(self.checkpoint_path, "w") as f:
                json.dump(checkpoint, f)
            # Save to DB
            await self.db.query(
                "UPSERT mission_checkpoint:fractal_nexus CONTENT $checkpoint",
                {"checkpoint": checkpoint},
            )
            logger.debug(f"💾 Checkpoint saved at iteration {self.batch_count}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    async def _load_checkpoint(self):
        """Load mission state from DB or local file."""
        checkpoint = None
        try:
            # Try DB first
            res = await self.db.query("SELECT * FROM mission_checkpoint:fractal_nexus")
            if res and isinstance(res, list) and len(res) > 0:
                result_item = res[0]
                # Handle both raw list and {'result': [...]} format
                records = result_item.get("result", []) if isinstance(result_item, dict) else result_item
                if records:
                    checkpoint = records[0]
                    logger.info("⚡ Resuming from SurrealDB checkpoint.")
            elif self.checkpoint_path.exists():
                with open(self.checkpoint_path) as f:
                    checkpoint = json.load(f)
                logger.info("⚡ Resuming from local checkpoint.")

            if checkpoint:
                self.batch_count = checkpoint.get("batch_count", 0)
                self.total_cycles = checkpoint.get("total_cycles", 0)
                self.num_rounds = checkpoint.get("num_rounds", DEFAULT_NUM_ROUNDS)
                self.stability_history = checkpoint.get("stability_history", [])
                logger.info(f"✓ Resumed: Iteration {self.batch_count}, Total Cycles: {self.total_cycles}")
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")


if __name__ == "__main__":
    mission = FractalNexusMission()
    asyncio.run(mission.run())
