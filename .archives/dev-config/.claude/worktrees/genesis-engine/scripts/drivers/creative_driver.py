"""
Creative Driver: Societal Evolution & Governance Simulation.
v1.0 - "The Civilization Edition"

Runs in parallel with Overnight Driver.
- Domain: Sociology, Ethics, Political Science.
- Logic: R-Zero Challenger (Crisis vs Governance).
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Internal imports
from cohezion.swarm.mass_simulator import MassSimulator


logger = logging.getLogger("creative")

# Constants
TARGET_SIMULATIONS = 500_000
END_TIME_HOUR = 8
BATCH_SIZE = 500


@dataclass
class SocietalState:
    epoch: int = 1
    stability: float = 1.0
    tech_level: float = 1.0

    def generate_crisis(self) -> dict:
        """Generate a societal crisis."""
        crises = [
            {"name": "Resource Scarcity", "resource_drain": 0.3},
            {"name": "AI Uprising", "control_loss": 0.5},
            {"name": "Solar Flare", "tech_damage": 0.8},
            {"name": "Pandemic", "pop_drain": 0.4},
            {"name": "Cultural Renaissance", "chaos_boost": 0.2},  # Positive crisis
        ]
        return random.choice(crises)

    def update(self, avg_unity: float):
        # If society is too unified, introduce chaos (stagnation)
        if avg_unity > 0.9:
            self.stability -= 0.1
            self.epoch += 1
            return True
        # If too chaotic, boost authoritarianism (order)
        if avg_unity < 0.3:
            self.stability += 0.1
            return False


class CreativeDriver:
    def __init__(self):
        self.simulator = MassSimulator(
            total_simulations=TARGET_SIMULATIONS,
            chunk_size=BATCH_SIZE,
            output_dir=Path("src/cohezion/knowledge_graph/universe_nodes/societal_evolution"),
        )
        self.state = SocietalState()
        self.total_completed = 0

    async def run_until_morning(self):
        logger.info("Starting Creative Simulation (Societal Evolution)...")

        while True:
            now = datetime.now()
            if now.hour == END_TIME_HOUR and now.minute > 0:
                break

            await self._run_batch()
            await asyncio.sleep(5)

    async def _run_batch(self):
        log_dir = self.simulator.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        crisis = self.state.generate_crisis()

        def process_sim(input_data: str, idx: int) -> dict:
            seed = random.randint(0, 10000)
            random.seed(seed)

            # --- CIVILIZATION SIM ---
            resilience = random.uniform(0.5, 1.5)
            policy = random.choice(["Authoritarian", "Libertarian", "Technocratic", "Anarchist"])

            # Crisis Impact
            survival_chance = resilience - crisis.get("resource_drain", 0)
            if policy == "Technocratic" and crisis["name"] == "AI Uprising":
                survival_chance -= 0.5  # Backfire

            # Result
            outcome = "Survived" if survival_chance > 0.5 else "Collapsed"
            unity = random.uniform(0.0, 1.0)
            if outcome == "Collapsed":
                unity = 0.0

            result_text = (
                f"Civ Seed {seed}: Policy {policy}. Crisis: {crisis['name']}.\n"
                f"Resilience: {resilience:.2f}. Outcome: {outcome} (Unity: {unity:.2f})."
            )

            # Log
            with open(log_dir / f"civ_{int(time.time())}_{idx}.txt", "w") as f:
                f.write(result_text)

            return {
                "final_coherence": unity,  # Map unity to coherence for stats
                "policy": policy,
                "outcome": outcome,
                "type": "societal",
            }

        inputs = [f"Simulate Civ {i}" for i in range(BATCH_SIZE)]

        chunk_result = await asyncio.to_thread(self.simulator.run_custom_chunk, int(time.time()), inputs, process_sim)

        # Update State
        u_scores = [r["final_coherence"] for r in chunk_result.raw_results if isinstance(r, dict)]
        if u_scores:
            avg = sum(u_scores) / len(u_scores)
            self.state.update(avg)

        self.total_completed += len(inputs)
        logger.info(
            f"[CREATIVE] Batch completed. Total: {self.total_completed}. Crisis: {crisis['name']}"
        )



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    driver = CreativeDriver()
    asyncio.run(driver.run_until_morning())
