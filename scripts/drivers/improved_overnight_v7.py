"""
Improved Overnight Simulation v7.0 - Evolved from Overnight v6 Analysis
=====================================================================

Based on findings from overnight_v6_20260217_001038:
- Mutation Rate: 0.5 (increased exploration)
- Learning Rate: 0.01 (found optimal)
- Convergence: Stable
- Score Trend: Stable
- 2.35M simulations validated learning effectiveness

Integrates findings into production-ready simulation.
"""

import asyncio
import json
import logging
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cohezion.core.persistence.surreal_client import SurrealClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [IMPROVED-v7] - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"/home/mike-anderson/nvme-simulations/logs/improved_v7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger("ImprovedOvernightV7")

END_TIME_HOUR = 7
MIN_RUNTIME_HOURS = 8.0


@dataclass
class EvolvedParameters:
    """Parameters evolved from overnight_v6 analysis."""

    # FLUME (evolved from 2.35M simulations)
    flume_coherence_base: float = 0.5
    flume_processing_depth: int = 50
    flume_semantic_noise: float = 0.1

    # RZero (optimized learning rates)
    rzero_initial_difficulty: float = 1.0
    rzero_solver_lr: float = 0.01  # Evolved from 0.05 → 0.01
    rzero_iterations: int = 100

    # Fractal (stable HIHO)
    fractal_initial_coherence: float = 0.5
    fractal_initial_energy: float = 100.0
    fractal_metabolic_cost: float = 0.5
    fractal_coherence_lr: float = 0.02

    # Mass (exploration params)
    mass_mutation_rate: float = 0.5  # Evolved from 0.1 → 0.5
    mass_alpha_range: float = 1.9
    mass_beta_range: float = 1.0
    mass_gamma_range: float = 2.0


class SurrealDBProductionStore:
    """Production-ready SurrealDB storage."""

    def __init__(self, session_id: str):
        self.session_id = session_id.replace("-", "_")
        self.client: Optional[SurrealClient] = None
        self.connected = False
        self._write_buffer = []
        self._buffer_size = 100

    async def connect(self) -> bool:
        try:
            self.client = SurrealClient(
                url="ws://localhost:8000/rpc", namespace="cohezion", database="universe"
            )
            await self.client.connect()
            await self._ensure_schema()
            self.connected = True
            logger.info("✅ SurrealDB production connected")
            return True
        except Exception as e:
            logger.error(f"❌ SurrealDB connection failed: {e}")
            return False

    async def _ensure_schema(self):
        """Ensure production schema exists."""
        try:
            await self.client.query("""
                DEFINE TABLE IF NOT EXISTS production_results SCHEMAFULL;
                DEFINE FIELD IF NOT EXISTS session_id ON production_results TYPE string;
                DEFINE FIELD IF NOT EXISTS simulation_type ON production_results TYPE string;
                DEFINE FIELD IF NOT EXISTS generation ON production_results TYPE int;
                DEFINE FIELD IF NOT EXISTS score ON production_results TYPE float;
                DEFINE FIELD IF NOT EXISTS coherence ON production_results TYPE float;
                DEFINE FIELD IF NOT EXISTS metrics ON production_results TYPE object;
                DEFINE FIELD IF NOT EXISTS timestamp ON production_results TYPE datetime;
            """)
        except Exception as e:
            logger.warning(f"Schema setup warning: {e}")

    async def write_result(self, sim_type: str, generation: int, result: dict):
        """Write result with buffering."""
        record = {
            "id": f"{self.session_id}_{sim_type}_g{generation}_{result.get('id', 'unknown')}",
            "session_id": self.session_id,
            "simulation_type": sim_type,
            "generation": generation,
            "score": result.get("score", 0),
            "coherence": result.get("coherence", 0.5),
            "metrics": result.get("metrics", {}),
            "timestamp": datetime.now().isoformat(),
        }

        self._write_buffer.append(record)

        if len(self._write_buffer) >= self._buffer_size:
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush write buffer to SurrealDB."""
        if not self._write_buffer or not self.connected:
            return

        try:
            for record in self._write_buffer:
                await self.client.query(f"""
                    INSERT INTO production_results {{
                        id: '{record["id"]}',
                        session_id: '{record["session_id"]}',
                        simulation_type: '{record["simulation_type"]}',
                        generation: {record["generation"]},
                        score: {record["score"]},
                        coherence: {record["coherence"]},
                        metrics: {json.dumps(record["metrics"])},
                        timestamp: '{record["timestamp"]}'
                    }}
                """)

            logger.debug(f"💾 Flushed {len(self._write_buffer)} records to SurrealDB")
            self._write_buffer.clear()

        except Exception as e:
            logger.warning(f"Buffer flush failed: {e}")

    async def close(self):
        await self._flush_buffer()
        if self.client:
            await self.client.close()
            self.connected = False


class ImprovedOvernightV7:
    """Improved overnight simulation with evolved parameters."""

    def __init__(self):
        self.session_id = f"improved_v7_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = time.time()
        self.store = SurrealDBProductionStore(self.session_id)
        self.params = EvolvedParameters()
        self.generation = 0
        self.total_sims = 0

    def should_continue(self) -> bool:
        now = datetime.now()
        elapsed = (time.time() - self.start_time) / 3600

        if now.hour >= END_TIME_HOUR and elapsed >= MIN_RUNTIME_HOURS:
            return False
        if elapsed >= MIN_RUNTIME_HOURS and now.hour >= END_TIME_HOUR:
            return False
        return True

    def evolve_params(self, scores: List[float]):
        """Evolve parameters based on performance."""
        if not scores:
            return

        avg_score = statistics.mean(scores)

        # Evolved from v6: mutation rate adapts to convergence
        if statistics.stdev(scores) < 0.1:
            self.params.mass_mutation_rate = max(
                0.1, self.params.mass_mutation_rate * 0.95
            )
        else:
            self.params.mass_mutation_rate = min(
                0.5, self.params.mass_mutation_rate * 1.05
            )

        # Learning rate already optimized at 0.01
        # Keep stable unless significant changes needed

        logger.info(
            f"🧬 Generation {self.generation} evolved: mutation={self.params.mass_mutation_rate:.3f}, score={avg_score:.3f}"
        )

    async def run_flume_batch(self, count: int) -> List[dict]:
        """Run FLUME simulations with evolved parameters."""
        results = []

        for i in range(count):
            coherence = self.params.flume_coherence_base
            for _ in range(self.params.flume_processing_depth):
                activation = math.tanh(coherence * 2 - 1)
                coherence = coherence * 0.9 + activation * 0.1

            coherence += random.gauss(0, self.params.flume_semantic_noise)
            coherence = max(0.3, min(0.9, coherence))

            results.append(
                {
                    "id": f"flume_{i}",
                    "score": coherence,
                    "coherence": coherence,
                    "metrics": {"layers": self.params.flume_processing_depth},
                }
            )

            if i % 10 == 0:
                await asyncio.sleep(0.001)

        return results

    async def run_rzero_batch(self, count: int) -> List[dict]:
        """Run R-Zero with evolved learning rate (0.01)."""
        results = []

        for i in range(count):
            score = 0.5
            for _ in range(self.params.rzero_iterations):
                gradient = random.gauss(0, 0.1) * (1.0 - score)
                score += self.params.rzero_solver_lr * gradient  # Using evolved LR
                score = max(0.0, min(1.0, score))

            results.append(
                {
                    "id": f"rzero_{i}",
                    "score": score,
                    "coherence": score,
                    "metrics": {"difficulty": self.params.rzero_initial_difficulty},
                }
            )

            if i % 10 == 0:
                await asyncio.sleep(0.001)

        return results

    async def run_fractal_batch(self, agents: int, steps: int) -> List[dict]:
        """Run fractal with evolved HIHO parameters."""
        agents_list = []
        for i in range(agents):
            agents_list.append(
                {
                    "id": f"agent_{i}",
                    "coherence": self.params.fractal_initial_coherence
                    + random.gauss(0, 0.1),
                    "energy": self.params.fractal_initial_energy,
                    "x": random.randint(0, 63),
                    "y": random.randint(0, 63),
                }
            )

        for step in range(steps):
            for agent in agents_list:
                # HIHO: drift to 0.5
                target = 0.5
                agent["coherence"] += (
                    target - agent["coherence"]
                ) * self.params.fractal_coherence_lr
                agent["coherence"] += random.gauss(0, 0.05)
                agent["coherence"] = max(0.0, min(1.0, agent["coherence"]))

                # Metabolism
                cost = self.params.fractal_metabolic_cost * (
                    1 + abs(agent["coherence"] - 0.5)
                )
                agent["energy"] -= cost

                # Movement
                agent["x"] = (agent["x"] + random.randint(-1, 1)) % 64
                agent["y"] = (agent["y"] + random.randint(-1, 1)) % 64

            agents_list = [a for a in agents_list if a["energy"] > 0]

            if step % 100 == 0:
                await asyncio.sleep(0.01)

        return [
            {
                "id": a["id"],
                "score": a["coherence"],
                "coherence": a["coherence"],
                "metrics": {"energy": a["energy"]},
            }
            for a in agents_list
        ]

    async def run_mass_batch(self, count: int) -> List[dict]:
        """Run mass parameter sweep with evolved mutation (0.5)."""
        results = []
        golden = 1.618033988749895

        for i in range(count):
            # Quasi-random with evolved mutation
            alpha = 0.1 + ((i * golden) % 1.0) * self.params.mass_alpha_range
            alpha += random.gauss(0, self.params.mass_mutation_rate * 0.2)

            beta = 0.5 + ((i * golden**2) % 1.0) * self.params.mass_beta_range
            beta += random.gauss(0, self.params.mass_mutation_rate * 0.1)

            gamma = -1.0 + ((i * golden**3) % 1.0) * self.params.mass_gamma_range
            gamma += random.gauss(0, self.params.mass_mutation_rate * 0.3)

            energy = alpha * 0.4 + beta * 0.3 + abs(gamma) * 0.3
            stability = 1.0 / (1.0 + abs(energy))

            results.append(
                {
                    "id": f"mass_{i}",
                    "score": stability,
                    "coherence": stability,
                    "metrics": {"alpha": alpha, "beta": beta, "gamma": gamma},
                }
            )

            if i % 10 == 0:
                await asyncio.sleep(0.001)

        return results

    async def run(self):
        """Main improved overnight loop."""
        logger.info("=" * 70)
        logger.info("🌙 IMPROVED OVERNIGHT SIMULATION v7.0")
        logger.info("=" * 70)
        logger.info(f"Session: {self.session_id}")
        logger.info(f"Based on: overnight_v6_20260217_001038")
        logger.info(
            f"Evolving parameters: mutation={self.params.mass_mutation_rate}, lr={self.params.rzero_solver_lr}"
        )
        logger.info("=" * 70)

        await self.store.connect()

        try:
            while self.should_continue():
                self.generation += 1
                logger.info(f"")
                logger.info(
                    f"🔄 Generation {self.generation} - {datetime.now().strftime('%H:%M')}"
                )

                # Run all phases
                flume_results = await self.run_flume_batch(500)
                for r in flume_results:
                    await self.store.write_result("FLUME", self.generation, r)

                rzero_results = await self.run_rzero_batch(500)
                for r in rzero_results:
                    await self.store.write_result("RZero", self.generation, r)

                fractal_results = await self.run_fractal_batch(100, 360)
                for r in fractal_results:
                    await self.store.write_result("Fractal", self.generation, r)

                mass_results = await self.run_mass_batch(500)
                for r in mass_results:
                    await self.store.write_result("Mass", self.generation, r)

                # Evolve based on performance
                all_scores = [
                    r["score"]
                    for r in flume_results
                    + rzero_results
                    + fractal_results
                    + mass_results
                ]
                self.evolve_params(all_scores)

                self.total_sims += (
                    len(flume_results)
                    + len(rzero_results)
                    + len(fractal_results)
                    + len(mass_results)
                )

                elapsed = (time.time() - self.start_time) / 3600
                logger.info(
                    f"📊 Total: {self.total_sims:,} sims, Elapsed: {elapsed:.2f}h"
                )

                await asyncio.sleep(1)

            await self._complete()

        finally:
            await self.store.close()

    async def _complete(self):
        """Complete and save results."""
        elapsed = (time.time() - self.start_time) / 3600

        results = {
            "session_id": self.session_id,
            "based_on": "overnight_v6_20260217_001038",
            "duration_hours": elapsed,
            "total_simulations": self.total_sims,
            "generations": self.generation,
            "final_mutation_rate": self.params.mass_mutation_rate,
            "final_learning_rate": self.params.rzero_solver_lr,
            "improvements": [
                "Evolved mutation rate from 0.1 to 0.5 for better exploration",
                "Optimized learning rate at 0.01 for stable convergence",
                "Implemented production-ready SurrealDB schema",
                "Added buffered writes for performance",
            ],
        }

        results_path = Path(
            f"/home/mike-anderson/nvme-simulations/improved_v7_{self.session_id}.json"
        )
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

        logger.info("")
        logger.info("=" * 70)
        logger.info("☀️ IMPROVED SIMULATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Duration: {elapsed:.2f} hours")
        logger.info(f"Generations: {self.generation}")
        logger.info(f"Total simulations: {self.total_sims:,}")
        logger.info(f"Results: {results_path}")
        logger.info("=" * 70)


async def main():
    sim = ImprovedOvernightV7()
    await sim.run()


if __name__ == "__main__":
    asyncio.run(main())
