import asyncio
import json
import logging
import multiprocessing
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List

from cohezion.swarm.universe_vector_engine import UniverseVectorEngine
from cohezion.swarm.hourly_mission_logger import HourlyMissionLogger
from cohezion.swarm.multimodal_reporter import MultimodalReporter
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.swarm.journey_tracker import JourneyTracker

logger = logging.getLogger(__name__)

def run_universe_scenario(config: Dict[str, Any]):
    """Target function for multiprocessing."""
    engine = UniverseVectorEngine(num_rounds=config["num_rounds"])
    results = engine.run_scenario(
        name=config["name"],
        momentum=config.get("momentum", 0.9),
        coupling=config.get("coupling", 1.0),
        hiho_target=config.get("hiho_target", 0.5),
        entropy=config.get("entropy", 0.02)
    )
    return results

class ScenarioMissionRunner:
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.output_dir = Path("src/cohezion/knowledge_graph/universe_nodes/simulations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.monitor = get_resource_monitor()
        self.logger_agent = HourlyMissionLogger(mission_id)
        self.scenarios = self._define_scenarios()

    def _define_scenarios(self):
        """Archetypal Universe Configurations."""
        return [
            {
                "name": "The_Void",
                "momentum": 0.5,
                "coupling": 0.2,
                "hiho_target": 0.1, # Shifted to low coherence
                "entropy": 0.1,    # High noise
                "num_rounds": 10_000_000
            },
            {
                "name": "Resonant_Lattice",
                "momentum": 0.98,
                "coupling": 1.5,
                "hiho_target": 0.5,
                "entropy": 0.005,  # Low noise, high order
                "num_rounds": 10_000_000
            },
            {
                "name": "The_Glitch",
                "momentum": 0.8,
                "coupling": 0.5,
                "hiho_target": 0.8, # Overconfident bias
                "entropy": 0.05,
                "num_rounds": 10_000_000
            },
            {
                "name": "Fractal_Nexus",
                "momentum": 0.9,
                "coupling": 1.0,
                "hiho_target": 0.5, # The Golden Mean
                "entropy": 0.02,
                "num_rounds": 10_000_000
            }
        ]

    async def run_multiverse(self):
        """Orchestrates the multiverse simulation."""
        logger.info(f"🌌 Launching Multiverse Scenario Mission: {self.mission_id}")

        # Check vitals before starting
        vitals = self.monitor.get_vitals()
        if self.monitor.critical_pressure:
            logger.warning(f"🚨 Skipping mission due to high resource pressure: {vitals}")
            return

        start_time = time.perf_counter()

        # Run in parallel
        # We cap at 4 processes to follow ResourceMonitor's guardrails
        with multiprocessing.Pool(processes=min(4, multiprocessing.cpu_count())) as pool:
            all_results = pool.map(run_universe_scenario, self.scenarios)

        duration = time.perf_counter() - start_time
        logger.info(f"✅ Multiverse Simulation Complete in {duration:.2f} seconds.")

        # Save aggregated report
        report_id = f"multiverse_{self.mission_id}_{int(time.time())}"
        output_file = self.output_dir / f"{report_id}.json"

        summary = {
            "mission_id": self.mission_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_duration_sec": duration,
            "vitals_at_start": vitals,
            "scenarios": all_results
        }

        output_file.write_text(json.dumps(summary, indent=2))

        # Persist to SurrealDB
        tracker = JourneyTracker()
        for res in all_results:
            tracker.log_step(
                agent_id="ScenarioRunner",
                action=f"Simulated Universe: {res['scenario_name']}",
                state=res,
                metrics={
                    "stability": res["mean_stability"],
                    "bright_spots": res["bright_spot_count"]
                }
            )

        # Log to hourly agent and get report content
        email_report = self.logger_agent.log_snapshot(
            vitals=self.monitor.get_vitals(),
            results=all_results,
            next_steps="Analyzing PCA clustering and cross-universe stability gradients."
        )

        # Multimodal synthesis
        reporter = MultimodalReporter()
        carousel_path = reporter.create_multiverse_carousel(all_results)

        print(email_report)
        print(f"\n🎡 Multimodal Carousel Generated: {carousel_path}")
        logger.info(f"💾 Results saved to {output_file}")

        return summary

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = ScenarioMissionRunner("nexus_alpha_v1")
    asyncio.run(runner.run_multiverse())
