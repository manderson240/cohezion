"""
Recursive Learning Simulation System v5.0
==========================================

Features:
- All agent journeys stored in SurrealDB in real-time
- Analysis of each round to extract patterns
- Parameter adjustment based on learned insights
- Continuous improvement across iterations
- Multi-generation evolution tracking
"""

import asyncio
import json
import logging
import math
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cohezion.core.persistence.surreal_client import SurrealClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [RECURSIVE] - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"/home/mike-anderson/nvme-simulations/logs/recursive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger("RecursiveLearningSimulation")


@dataclass
class LearningState:
    """State that persists and improves across iterations."""

    generation: int = 0
    best_parameters: Dict[str, float] = field(default_factory=dict)
    parameter_history: List[Dict] = field(default_factory=list)
    convergence_rate: float = 0.0
    avg_coherence: float = 0.5
    energy_efficiency: float = 0.0
    mutation_rate: float = 0.1
    learning_rate: float = 0.05

    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "best_parameters": self.best_parameters,
            "convergence_rate": self.convergence_rate,
            "avg_coherence": self.avg_coherence,
            "energy_efficiency": self.energy_efficiency,
            "mutation_rate": self.mutation_rate,
            "learning_rate": self.learning_rate,
        }


class SurrealDBLearningStore:
    """Store and retrieve learning data from SurrealDB."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.client: Optional[SurrealClient] = None
        self.connected = False

    async def connect(self) -> bool:
        """Connect to SurrealDB."""
        try:
            self.client = SurrealClient(
                url="ws://localhost:8000/rpc", namespace="cohezion", database="universe"
            )
            await self.client.connect()
            await self.client.setup_schema()
            self.connected = True
            logger.info("✅ Connected to SurrealDB for recursive learning")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to SurrealDB: {e}")
            return False

    async def store_agent_journey(self, agent_data: dict) -> bool:
        """Store individual agent journey in SurrealDB."""
        if not self.connected:
            return False

        try:
            journey_record = {
                "id": f"journey:{self.session_id}_{agent_data['id']}",
                "session_id": self.session_id,
                "agent_id": agent_data["id"],
                "generation": agent_data.get("generation", 0),
                "start_time": agent_data.get("start_time"),
                "end_time": datetime.now().isoformat(),
                "coherence": agent_data.get("coherence", 0.5),
                "energy": agent_data.get("energy", 0),
                "position": {"x": agent_data.get("x", 0), "y": agent_data.get("y", 0)},
                "metrics": agent_data.get("metrics", {}),
                "actions": agent_data.get("actions", []),
            }

            # Store in SurrealDB - use underscore-safe IDs
            safe_session = self.session_id.replace("-", "_")
            safe_agent_id = agent_data["id"].replace("-", "_")
            await self.client.query(
                f"CREATE journey:{safe_session}_{safe_agent_id} CONTENT {json.dumps(journey_record)}"
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️  Failed to store journey: {e}")
            return False

    async def store_simulation_result(self, result: dict) -> bool:
        """Store simulation result for analysis."""
        if not self.connected:
            return False

        try:
            result_record = {
                "id": f"result:{self.session_id}_{result['id']}",
                "session_id": self.session_id,
                "simulation_id": result["id"],
                "score": result.get("score", 0),
                "coherence": result.get("coherence", 0.5),
                "metrics": result.get("metrics", {}),
                "timestamp": datetime.now().isoformat(),
            }

            # Store in SurrealDB - use underscore-safe IDs
            safe_session = self.session_id.replace("-", "_")
            safe_result_id = result["id"].replace("-", "_")
            await self.client.query(
                f"CREATE result:{safe_session}_{safe_result_id} CONTENT {json.dumps(result_record)}"
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️  Failed to store result: {e}")
            return False

    async def analyze_generation(self, generation: int) -> dict:
        """Analyze all results from a generation to extract insights."""
        if not self.connected:
            return {}

        try:
            # Query all results for this session
            query = f"""
                SELECT * FROM result 
                WHERE session_id = '{self.session_id}'
            """
            results = await self.client.query(query)

            if not results or not results[0].get("result"):
                return {}

            data = results[0]["result"]

            # Calculate statistics
            scores = [r.get("score", 0) for r in data if "score" in r]
            coherences = [r.get("coherence", 0.5) for r in data if "coherence" in r]

            analysis = {
                "generation": generation,
                "total_sims": len(data),
                "avg_score": statistics.mean(scores) if scores else 0,
                "std_score": statistics.stdev(scores) if len(scores) > 1 else 0,
                "best_score": max(scores) if scores else 0,
                "worst_score": min(scores) if scores else 0,
                "avg_coherence": statistics.mean(coherences) if coherences else 0.5,
                "convergence": 1.0
                - (statistics.stdev(coherences) if len(coherences) > 1 else 0.5),
            }

            # Store analysis
            await self.client.query(
                f"CREATE analysis:{self.session_id}_gen{generation} CONTENT {json.dumps(analysis)}"
            )

            return analysis

        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            return {}

    async def get_best_parameters(self) -> dict:
        """Retrieve best parameters from previous generations."""
        if not self.connected:
            return {}

        try:
            query = f"""
                SELECT * FROM result 
                WHERE session_id = '{self.session_id}'
                ORDER BY score DESC
                LIMIT 10
            """
            results = await self.client.query(query)

            if results and results[0].get("result"):
                best = results[0]["result"][0]
                return best.get("metrics", {})

            return {}
        except Exception as e:
            logger.warning(f"⚠️  Could not retrieve best parameters: {e}")
            return {}

    async def close(self):
        """Close database connection."""
        if self.client:
            await self.client.close()
            self.connected = False


class RecursiveSimulationEngine:
    """Simulation engine that learns and improves across iterations."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = (
            session_id or f"recursive-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.archive_dir = Path("/home/mike-anderson/nvme-simulations")
        self.store = SurrealDBLearningStore(self.session_id)
        self.learning_state = LearningState()
        self.generation_results = []

    async def initialize(self):
        """Initialize SurrealDB connection."""
        await self.store.connect()

    def evolve_parameters(self, analysis: dict) -> dict:
        """Evolve simulation parameters based on analysis."""
        old_state = self.learning_state.to_dict()

        # Adjust mutation rate based on convergence
        if analysis.get("convergence", 0) > 0.8:
            # High convergence = lower mutation (exploit)
            self.learning_state.mutation_rate *= 0.9
        else:
            # Low convergence = higher mutation (explore)
            self.learning_state.mutation_rate = min(
                0.3, self.learning_state.mutation_rate * 1.1
            )

        # Adjust learning rate based on improvement
        if analysis.get("avg_score", 0) > old_state.get("avg_score", 0):
            self.learning_state.learning_rate *= 1.05  # Keep improving
        else:
            self.learning_state.learning_rate *= 0.95  # Slow down

        self.learning_state.learning_rate = max(
            0.01, min(0.2, self.learning_state.learning_rate)
        )

        # Extract best parameters to guide next generation
        if analysis.get("best_parameters"):
            for key, value in analysis["best_parameters"].items():
                if key not in self.learning_state.best_parameters:
                    self.learning_state.best_parameters[key] = value
                else:
                    # Move toward best value
                    current = self.learning_state.best_parameters[key]
                    target = value
                    lr = self.learning_state.learning_rate
                    self.learning_state.best_parameters[key] = current + lr * (
                        target - current
                    )

        self.learning_state.generation += 1
        self.learning_state.convergence_rate = analysis.get("convergence", 0)
        self.learning_state.avg_coherence = analysis.get("avg_coherence", 0.5)

        # Log evolution
        logger.info(f"🧬 Generation {self.learning_state.generation} evolved:")
        logger.info(
            f"   Mutation rate: {old_state.get('mutation_rate', 0.1):.3f} → {self.learning_state.mutation_rate:.3f}"
        )
        logger.info(
            f"   Learning rate: {old_state.get('learning_rate', 0.05):.3f} → {self.learning_state.learning_rate:.3f}"
        )
        logger.info(f"   Convergence: {self.learning_state.convergence_rate:.3f}")

        return self.learning_state.best_parameters

    async def run_learning_iteration(
        self, iteration_type: str, count: int, duration_minutes: float
    ) -> dict:
        """Run one learning iteration with SurrealDB storage."""
        logger.info("")
        logger.info(
            f"🔄 LEARNING ITERATION {self.learning_state.generation + 1}: {iteration_type}"
        )
        logger.info(f"   Target: {count} simulations")
        logger.info(f"   Duration: {duration_minutes} minutes")

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        results = []

        # Get evolved parameters
        best_params = self.learning_state.best_parameters
        mutation_rate = self.learning_state.mutation_rate

        for i in range(count):
            # Check time limit
            if time.time() > end_time:
                logger.info(f"⏰ Time limit reached at {i}/{count}")
                break

            # Mutate parameters
            params = {}
            for key, base_value in best_params.items():
                mutation = random.gauss(0, mutation_rate)
                params[key] = base_value + mutation

            # Run simulation with evolved parameters
            if iteration_type == "FLUME":
                result = self._simulate_flume_with_params(i, params)
            elif iteration_type == "RZero":
                result = self._simulate_rzero_with_params(i, params)
            elif iteration_type == "Fractal":
                result = await self._simulate_fractal_agent(i, params)
            else:
                result = self._simulate_mass_with_params(i, params)

            results.append(result)

            # Store in SurrealDB immediately
            await self.store.store_simulation_result(result)

            # Progress
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                remaining = (end_time - time.time()) / 60
                logger.info(
                    f"   Progress: {i + 1}/{count}, {elapsed / 60:.1f}m elapsed, {remaining:.1f}m remaining"
                )

            # Small delay to allow DB writes and prevent overload
            if i % 10 == 0:
                await asyncio.sleep(0.01)

        # Analyze this generation
        analysis = await self.store.analyze_generation(self.learning_state.generation)

        # Evolve for next generation
        self.evolve_parameters(analysis)

        return {
            "iteration": self.learning_state.generation,
            "type": iteration_type,
            "count": len(results),
            "analysis": analysis,
            "duration_seconds": time.time() - start_time,
        }

    def _simulate_flume_with_params(self, idx: int, params: dict) -> dict:
        """FLUME simulation with learned parameters."""
        coherence = params.get("coherence_base", 0.5) + random.gauss(
            0, params.get("coherence_noise", 0.1)
        )
        coherence = max(0.3, min(0.9, coherence))

        # Generate semantic vector influenced by parameters
        semantic_vector = []
        for i in range(12):
            base = params.get(f"semantic_{i}", 0.5)
            val = base + random.gauss(0, params.get("semantic_noise", 0.1))
            semantic_vector.append(round(max(0, min(1, val)), 4))

        return {
            "id": f"flume_gen{self.learning_state.generation}_{idx}",
            "score": coherence,
            "coherence": coherence,
            "metrics": {
                "semantic_vector": semantic_vector,
                "generation": self.learning_state.generation,
            },
        }

    def _simulate_rzero_with_params(self, idx: int, params: dict) -> dict:
        """R-Zero simulation with learned parameters."""
        difficulty = params.get("difficulty", 1.0)
        learning_rate = params.get("solver_lr", 0.01)

        # Iterative solving
        score = 0.5
        for _ in range(50 + int(difficulty * 20)):
            gradient = random.gauss(0, 0.1) * (1.0 - score)
            score += learning_rate * gradient
            score = max(0.0, min(1.0, score))

        return {
            "id": f"rzero_gen{self.learning_state.generation}_{idx}",
            "score": score,
            "coherence": score,
            "metrics": {
                "difficulty": difficulty,
                "generation": self.learning_state.generation,
            },
        }

    async def _simulate_fractal_agent(self, idx: int, params: dict) -> dict:
        """Fractal agent simulation with learned behavior."""
        coherence = params.get("initial_coherence", 0.5)
        energy = params.get("initial_energy", 100.0)

        # Agent journey
        actions = []
        for step in range(100):
            # HIHO: drift toward 0.5
            target = 0.5
            learning_rate = params.get("coherence_lr", 0.02)
            coherence += (target - coherence) * learning_rate + random.gauss(0, 0.05)
            coherence = max(0.0, min(1.0, coherence))

            # Energy metabolism
            cost = params.get("metabolic_cost", 0.5) * (1 + abs(coherence - 0.5))
            energy -= cost

            actions.append({"step": step, "coherence": coherence, "energy": energy})

            if energy <= 0:
                break

        agent_data = {
            "id": f"agent_gen{self.learning_state.generation}_{idx}",
            "generation": self.learning_state.generation,
            "start_time": datetime.now().isoformat(),
            "coherence": coherence,
            "energy": energy,
            "x": random.randint(0, 63),
            "y": random.randint(0, 63),
            "metrics": {"final_coherence": coherence, "survival_steps": len(actions)},
            "actions": actions[:10],  # Store first 10 actions
        }

        # Store full journey in SurrealDB
        await self.store.store_agent_journey(agent_data)

        return {
            "id": agent_data["id"],
            "score": coherence,
            "coherence": coherence,
            "metrics": agent_data["metrics"],
        }

    def _simulate_mass_with_params(self, idx: int, params: dict) -> dict:
        """Mass parameter sweep with learned parameters."""
        # Use golden ratio for quasi-random sampling
        golden = 1.618033988749895

        alpha = params.get("alpha_min", 0.1) + ((idx * golden) % 1.0) * (
            params.get("alpha_max", 2.0) - params.get("alpha_min", 0.1)
        )
        beta = params.get("beta_min", 0.5) + ((idx * golden**2) % 1.0) * (
            params.get("beta_max", 1.5) - params.get("beta_min", 0.5)
        )
        gamma = params.get("gamma_min", -1.0) + ((idx * golden**3) % 1.0) * (
            params.get("gamma_max", 1.0) - params.get("gamma_min", -1.0)
        )

        # Calculate energy
        energy = alpha * 0.4 + beta * 0.3 + abs(gamma) * 0.3 + random.gauss(0, 0.1)
        stability = 1.0 / (1.0 + abs(energy))

        return {
            "id": f"mass_gen{self.learning_state.generation}_{idx}",
            "score": stability,
            "coherence": stability,
            "metrics": {
                "alpha": alpha,
                "beta": beta,
                "gamma": gamma,
                "energy": energy,
                "stability": stability,
                "generation": self.learning_state.generation,
            },
        }

    async def run_full_recursive_simulation(
        self,
        iterations_per_phase: int = 3,
        sims_per_iteration: int = 1000,
        minutes_per_iteration: float = 20,
    ):
        """Run complete recursive learning simulation."""
        logger.info("=" * 70)
        logger.info("🧬 RECURSIVE LEARNING SIMULATION v5.0")
        logger.info("=" * 70)
        logger.info(f"Session: {self.session_id}")
        logger.info(f"Iterations per phase: {iterations_per_phase}")
        logger.info(f"Sims per iteration: {sims_per_iteration}")
        logger.info(f"Minutes per iteration: {minutes_per_iteration}")
        logger.info("=" * 70)

        all_results = []

        try:
            # Initialize with random parameters
            self.learning_state.best_parameters = {
                "coherence_base": 0.5,
                "coherence_noise": 0.1,
                "semantic_noise": 0.1,
                "difficulty": 1.0,
                "solver_lr": 0.01,
                "initial_coherence": 0.5,
                "initial_energy": 100.0,
                "coherence_lr": 0.02,
                "metabolic_cost": 0.5,
                "alpha_min": 0.1,
                "alpha_max": 2.0,
                "beta_min": 0.5,
                "beta_max": 1.5,
                "gamma_min": -1.0,
                "gamma_max": 1.0,
            }

            # Add semantic parameters
            for i in range(12):
                self.learning_state.best_parameters[f"semantic_{i}"] = 0.5

            # Phase 1: FLUME with learning
            for iteration in range(iterations_per_phase):
                result = await self.run_learning_iteration(
                    "FLUME", sims_per_iteration, minutes_per_iteration
                )
                all_results.append(result)

            # Phase 2: R-Zero with learning
            for iteration in range(iterations_per_phase):
                result = await self.run_learning_iteration(
                    "RZero", sims_per_iteration, minutes_per_iteration
                )
                all_results.append(result)

            # Phase 3: Fractal with learning
            for iteration in range(iterations_per_phase):
                result = await self.run_learning_iteration(
                    "Fractal",
                    sims_per_iteration // 10,
                    minutes_per_iteration,  # Fewer agents
                )
                all_results.append(result)

            # Phase 4: Mass with learning
            for iteration in range(iterations_per_phase):
                result = await self.run_learning_iteration(
                    "Mass", sims_per_iteration, minutes_per_iteration
                )
                all_results.append(result)

            # Save final results
            self._save_results(all_results)

        finally:
            await self.store.close()

    def _save_results(self, all_results: List[dict]):
        """Save comprehensive results."""
        final_data = {
            "session_id": self.session_id,
            "final_learning_state": self.learning_state.to_dict(),
            "iterations": all_results,
            "timestamp": datetime.now().isoformat(),
        }

        results_path = self.archive_dir / f"recursive_results_{self.session_id}.json"
        with open(results_path, "w") as f:
            json.dump(final_data, f, indent=2)

        logger.info("")
        logger.info("=" * 70)
        logger.info("🌟 RECURSIVE SIMULATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total iterations: {len(all_results)}")
        logger.info(f"Final generation: {self.learning_state.generation}")
        logger.info(f"Final convergence: {self.learning_state.convergence_rate:.3f}")
        logger.info(f"Results saved: {results_path}")
        logger.info("=" * 70)


async def main():
    engine = RecursiveSimulationEngine()
    await engine.initialize()

    # Run 3 hours of recursive learning (9 iterations × 20 min)
    await engine.run_full_recursive_simulation(
        iterations_per_phase=3,
        sims_per_iteration=1000,
        minutes_per_iteration=15,  # 15 min per iteration = 3 hours total
    )


if __name__ == "__main__":
    asyncio.run(main())
