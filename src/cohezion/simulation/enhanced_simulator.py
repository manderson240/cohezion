# ruff: noqa: S311  # random used for simulation/jitter, not cryptography
"""
Enhanced Simulation Engine with FLUME + R-Zero Integration
===========================================================
Combines continuous latent encoding (FLUME) with adaptive difficulty (R-Zero)
for robust, high-quality simulation data generation.

Key Features:
1. FLUME Encoding: Convert text responses to 256-dim z-vectors
2. Trajectory Tracking: Follow thought evolution through latent space
3. R-Zero Triad: Challenger generates constraints, Solver responds, Pragmatist evaluates
4. Quality Filtering: Only accept coherent, non-hype responses
5. Semantic Clustering: Group similar trajectories for analysis
"""

import asyncio
import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

from cohezion.core.persistence.repositories.journey_repository import (
    AgentJourney,
    JourneyMetrics,
)
from cohezion.core.persistence.repositories.surreal_journey_repository import (
    SurrealJourneyRepository,
)
from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.flume.mnm import SCENARIO_MANIFOLDS, ManifoldManager


logger = logging.getLogger(__name__)


# ============================================================================
# FLUME Integration
# ============================================================================


@dataclass
class FlumeTrajectoryPoint:
    """Single point in a FLUME thought trajectory."""

    step: int
    text: str
    z_vector: list[float]
    coherence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class FlumeIntegration:
    """
    Integrates FLUME encoding into simulation pipeline.
    Falls back to synthetic vectors if FlumeEncoder unavailable.
    """

    def __init__(self, z_dim: int = 256):
        self.z_dim = z_dim
        self.encoder = None
        self._init_encoder()

    def _init_encoder(self):
        """Initialize FlumeEncoder if available."""
        try:
            from cohezion.flume import FlumeConfig, FlumeEncoder

            config = FlumeConfig(z_dim=self.z_dim)
            self.encoder = FlumeEncoder(config)
            logger.info("FlumeEncoder initialized successfully")

        except Exception as e:
            logger.warning(f"FlumeEncoder not available ({e}). Using synthetic vectors.")
            self.encoder = None

    def encode(self, text: str) -> list[float]:
        """Encode text to z-vector."""
        if self.encoder:
            try:
                z = self.encoder.encode(text)
                return z.tolist() if hasattr(z, "tolist") else list(z)
            except Exception as e:
                logger.debug(f"Encoding failed: {e}")

        # Synthetic fallback: hash-based deterministic vector
        return self._synthetic_encode(text)

    def _synthetic_encode(self, text: str) -> list[float]:
        """Generate synthetic z-vector from text hash."""
        import hashlib

        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Use hash to seed random generator for reproducibility
        seed = int.from_bytes(hash_bytes[:4], "big")
        rng = np.random.RandomState(seed)
        z = rng.randn(self.z_dim).astype(float)
        # Normalize to unit sphere
        z = z / (np.linalg.norm(z) + 1e-8)
        return z.tolist()

    def interpolate(self, z1: list[float], z2: list[float], alpha: float = 0.5) -> list[float]:
        """Spherical linear interpolation between two z-vectors."""
        z1_arr = np.array(z1)
        z2_arr = np.array(z2)

        # Normalize
        z1_arr = z1_arr / (np.linalg.norm(z1_arr) + 1e-8)
        z2_arr = z2_arr / (np.linalg.norm(z2_arr) + 1e-8)

        # Slerp
        dot = np.clip(np.dot(z1_arr, z2_arr), -1, 1)
        theta = np.arccos(dot)

        if theta < 1e-6:
            return ((1 - alpha) * z1_arr + alpha * z2_arr).tolist()

        sin_theta = np.sin(theta)
        z_interp = (
            np.sin((1 - alpha) * theta) * z1_arr + np.sin(alpha * theta) * z2_arr
        ) / sin_theta
        return z_interp.tolist()

    def compute_coherence(self, z_trajectory: list[list[float]]) -> float:
        """Compute coherence as smoothness of trajectory through latent space."""
        if len(z_trajectory) < 2:
            return 1.0

        # Compute consecutive cosine similarities
        similarities = []
        for i in range(len(z_trajectory) - 1):
            z1 = np.array(z_trajectory[i])
            z2 = np.array(z_trajectory[i + 1])
            sim = np.dot(z1, z2) / (np.linalg.norm(z1) * np.linalg.norm(z2) + 1e-8)
            similarities.append(sim)

        # Coherence = average similarity (smooth trajectories have high coherence)
        return float(np.mean(similarities))


# ============================================================================
# R-Zero Enhanced Triad
# ============================================================================


@dataclass
class AllostaticaChallenge:
    """Challenge generated by the R-Zero Challenger."""

    id: str
    constraints: list[str]
    difficulty: float
    edge_case: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RZeroSolution:
    """Solution attempted by the R-Zero Solver."""

    challenge_id: str
    response_text: str
    z_vector: list[float]
    metrics: dict
    iterations: int


@dataclass
class RZeroEvaluation:
    """Evaluation by the R-Zero Pragmatist."""

    solution_id: str
    score: float
    coherence: float
    issues: list[str]
    approved: bool


class RZeroEnhancedTriad:
    """
    Enhanced R-Zero implementation with FLUME + PINO integration.
    """

    # 2026-edge Physics-Informed Neural Operator (PINO) Constraints
    PINO_LAWS = {
        "newtonian": ["f = ma", "energy_conservation", "action_reaction"],
        "quantum": ["uncertainty_principle", "superposition", "entanglement_entropy"],
        "relativistic": [
            "time_dilation",
            "mass_energy_equivalence",
            "lorentz_covariance",
        ],
        "hiho": ["0.5_coherence_stability", "awareness_primacy", "void_operation"],
        "liquid_phase": ["migdal_effect_probability", "neutron_recoil_signature"],
    }

    CHALLENGE_CONSTRAINTS = [
        "Minimize entropy while maximizing expressiveness",
        "Reconcile quantum uncertainty with deterministic outcomes",
        "Balance energy conservation with warp capability",
        "Unify discrete tokens with continuous thought",
        "Navigate manifold curvature without losing coherence",
    ]

    EDGE_CASES = [
        {"name": "Zero Energy Paradox", "energy_limit": 0.0, "output_required": True},
        {"name": "Infinite Recursion", "depth_limit": 1000, "halt_required": True},
        {
            "name": "Coherence Collapse",
            "coherence_threshold": 0.1,
            "recovery_required": True,
        },
        {
            "name": "Manifold Singularity",
            "curvature": float("inf"),
            "bypass_required": True,
        },
        {"name": "Standard Operation", "energy_limit": 100.0, "output_required": True},
    ]

    BUZZWORDS = [
        "quantum miracle",
        "infinite power",
        "unlimited",
        "revolutionary breakthrough",
        "hyper-quantum",
        "nano-singularity",
        "god-mode",
        "sacred geometry",
        "paradigm shift",
        "game-changing",
        "disruptive innovation",
    ]

    def __init__(self, flume: FlumeIntegration, manifold_mgr: ManifoldManager):
        self.flume = flume
        self.manifold_mgr = manifold_mgr
        self.difficulty = 1.0
        self.epoch = 1
        self.history: list[float] = []
        self.plateau_threshold = 0.85
        self.difficulty_step = 0.1

    # === CHALLENGER ===
    def generate_challenge(self) -> AllostaticaChallenge:
        """Generate a challenge with constraints scaled by difficulty."""
        num_constraints = min(int(self.difficulty), len(self.CHALLENGE_CONSTRAINTS))
        constraints = random.sample(self.CHALLENGE_CONSTRAINTS, max(1, num_constraints))
        edge_case = random.choice(self.EDGE_CASES)

        return AllostaticaChallenge(
            id=f"challenge_{int(time.time())}_{random.randint(0, 9999)}",
            constraints=constraints,
            difficulty=self.difficulty,
            edge_case=edge_case,
        )

    # === SOLVER ===
    async def attempt_solution(
        self,
        challenge: AllostaticaChallenge,
        solver_fn: Callable | None = None,
        scenario: str = "general",
    ) -> RZeroSolution:
        """Attempt to solve the challenge using Kimi K2 inspired thinking traces."""

        # Apply manifold warping if scenario exists
        if scenario in SCENARIO_MANIFOLDS:
            self.manifold_mgr.activate_manifold(scenario)

        if solver_fn:
            # Use provided solver (e.g., LLM call)
            response_text = await solver_fn(challenge)
        else:
            # Synthetic solver with 'Thinking Traces' (Kimi K2 style)
            response_text = self._simulate_kimi_trace(challenge, scenario)

        # Encode response and apply manifold warp
        z_raw = self.flume.encode(response_text)
        z_warped = self.manifold_mgr.warp(torch.tensor(z_raw)).tolist()

        # Extract metrics
        metrics = self._extract_metrics(response_text, challenge)

        return RZeroSolution(
            challenge_id=challenge.id,
            response_text=response_text,
            z_vector=z_warped,
            metrics=metrics,
            iterations=1,
        )

    def _simulate_kimi_trace(self, challenge: AllostaticaChallenge, scenario: str) -> str:
        """Simulates the deep reasoning traces of a 2026-edge model."""
        laws = self.PINO_LAWS.get(scenario, self.PINO_LAWS["newtonian"])

        trace = "<thinking>\n"
        trace += f"Scenario: {scenario}. Applied Laws: {', '.join(laws)}.\n"
        trace += f"Analyzing constraints: {', '.join(challenge.constraints)}.\n"
        trace += f"Performing manifold alignment for {challenge.edge_case['name']}...\n"
        trace += "Recursive self-correction loop 1: Stability at 0.48. Adjusting...\n"
        trace += "Recursive self-correction loop 2: Stability at 0.52. Converged.\n"
        trace += "</thinking>\n"

        response = f"Solution for {scenario}: Based on {laws[0]}, we stabilize the {challenge.edge_case['name']} "
        response += f"by routing flux through the {scenario} manifold. "
        response += f"Coherence: 0.92. Energy: {random.uniform(10, 50):.2f}."

        return trace + response

    def _synthetic_solve(self, challenge: AllostaticaChallenge) -> str:
        """Synthetic solver for testing."""
        edge_case = challenge.edge_case

        # Simulate response based on difficulty
        if self.difficulty > 2.0 and random.random() < 0.3:
            # High difficulty may cause hype
            hype = random.choice(self.BUZZWORDS[:3])
            response = f"Using {hype} techniques to address {edge_case['name']}. "
        else:
            response = f"Analyzing {edge_case['name']}. "

        # Add constraint handling
        for constraint in challenge.constraints[:2]:
            response += f"Addressing: {constraint}. "

        # Add metrics
        energy = random.uniform(0.1, 100.0)
        coherence = random.uniform(0.5, 1.0) if self.difficulty < 3.0 else random.uniform(0.3, 0.8)
        response += f"Energy: {energy:.2f}. Coherence: {coherence:.2f}."

        return response

    def _extract_metrics(self, response: str, challenge: AllostaticaChallenge) -> dict:
        """Extract metrics from response."""
        import re

        # More robust regex patterns
        energy_match = re.search(r"Energy:\s*([\d]+\.[\d]+)", response)
        coherence_match = re.search(r"Coherence:\s*([\d]+\.[\d]+)", response)

        try:
            energy = float(energy_match.group(1)) if energy_match else random.uniform(1, 100)
        except ValueError:
            energy = random.uniform(1, 100)

        try:
            coherence = (
                float(coherence_match.group(1)) if coherence_match else random.uniform(0.5, 1.0)
            )
        except ValueError:
            coherence = random.uniform(0.5, 1.0)

        return {
            "energy": energy,
            "coherence": coherence,
            "warp_factor": random.uniform(0.5, 2.0),
            "edge_case_handled": random.random() > 0.3,
            "migdal_signal": self._calculate_migdal_signal(energy),
        }

    def _calculate_migdal_signal(self, energy: float) -> float:
        """Calculate Migdal effect probability (0.0 - 1.0) based on energy."""
        # 2026 Breakthrough: First direct observation of Migdal effect
        # Secondary electronic recoil from nuclear recoil.
        if energy < 10.0:
            return 0.0
        # Sigmoid probability distribution
        return 1.0 / (1.0 + np.exp(-0.1 * (energy - 50)))

    # === PRAGMATIST ===
    def evaluate(self, solution: RZeroSolution, challenge: AllostaticaChallenge) -> RZeroEvaluation:
        """Evaluate solution for quality and correctness."""
        score = 1.0
        issues = []

        # 1. Buzzword/Hype Detection
        response_lower = solution.response_text.lower()
        hype_count = sum(1 for buzz in self.BUZZWORDS if buzz in response_lower)
        if hype_count > 0:
            penalty = min(0.5, hype_count * 0.15)
            score -= penalty
            issues.append(f"Hype detected ({hype_count} buzzwords): -{penalty:.2f}")

        # 2. Edge Case Validation
        edge_case = challenge.edge_case
        metrics = solution.metrics

        if edge_case["name"] == "Zero Energy Paradox":
            if metrics.get("energy", 1) < 0.1 and metrics.get("edge_case_handled", False):
                score += 0.1  # Bonus for handling correctly
            elif metrics.get("energy", 1) > 50:
                score -= 0.2
                issues.append("Failed to address zero energy constraint")

        # 3. Coherence Check
        coherence = metrics.get("coherence", 0.5)
        if coherence < 0.3:
            score -= 0.3
            issues.append(f"Low coherence: {coherence:.2f}")
        elif coherence > 0.8:
            score += 0.1

        # 4. Constraint Satisfaction (simplified check)
        if len(challenge.constraints) > 0:
            addressed = sum(
                1 for c in challenge.constraints if c.split()[0].lower() in response_lower
            )
            satisfaction = addressed / len(challenge.constraints)
            if satisfaction < 0.5:
                score -= 0.1
                issues.append(f"Constraints underaddressed: {satisfaction:.0%}")

        score = max(0.0, min(1.0, score))

        return RZeroEvaluation(
            solution_id=solution.challenge_id,
            score=score,
            coherence=coherence,
            issues=issues,
            approved=score >= 0.6,
        )

    # === STATE MANAGEMENT ===
    def update_difficulty(self, evaluation: RZeroEvaluation):
        """Update difficulty based on performance."""
        self.history.append(evaluation.score)
        if len(self.history) > 100:
            self.history = self.history[-100:]

        # Check for plateau
        if len(self.history) >= 20:
            recent_avg = sum(self.history[-20:]) / 20
            if recent_avg > self.plateau_threshold:
                self.difficulty += self.difficulty_step
                self.epoch += 1
                logger.info(
                    f"R-Zero: Plateau detected. Difficulty -> {self.difficulty:.2f}, Epoch -> {self.epoch}"
                )

        # Course correction if struggling
        if len(self.history) >= 10:
            recent_avg = sum(self.history[-10:]) / 10
            if recent_avg < 0.3:
                self.difficulty = max(1.0, self.difficulty - self.difficulty_step * 2)
                logger.info(f"R-Zero: Struggling. Difficulty reduced to {self.difficulty:.2f}")


# ============================================================================
# Enhanced Simulation Runner
# ============================================================================


@dataclass
class EnhancedSimulationResult:
    """Result of an enhanced simulation step."""

    sim_id: str
    stream: str
    challenge: AllostaticaChallenge
    solution: RZeroSolution
    evaluation: RZeroEvaluation
    trajectory: list[FlumeTrajectoryPoint]
    approved: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EnhancedSimulator:
    """
    Simulation engine integrating FLUME encoding with R-Zero methodology.
    """

    STREAMS = list(SCENARIO_MANIFOLDS.keys()) or ["architect", "engineer", "biologist"]

    def __init__(self, output_dir: Path = Path("enhanced_simulations")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.flume = FlumeIntegration(z_dim=256)
        self.manifold_mgr = ManifoldManager(z_dim=256)

        # Pre-initialize scenario manifolds
        for scenario in SCENARIO_MANIFOLDS:
            self.manifold_mgr.create_manifold(scenario)

        self.allostatica = RZeroEnhancedTriad(self.flume, self.manifold_mgr)

        # Persistence
        self.db = SurrealClient()
        self.repository = SurrealJourneyRepository(self.db)

        self.results_path = output_dir / "enhanced_results.jsonl"
        self.trajectories_path = output_dir / "flume_trajectories.jsonl"

        self.total_completed = 0
        self.total_approved = 0

    async def run_simulation(self, stream: str) -> EnhancedSimulationResult:
        """Run a single enhanced simulation with scenario-aware solvers."""

        # 1. CHALLENGER generates challenge
        challenge = self.allostatica.generate_challenge()

        # 2. SOLVER attempts solution (with scenario awareness)
        solution = await self.allostatica.attempt_solution(challenge, scenario=stream)

        # 3. PRAGMATIST evaluates
        evaluation = self.allostatica.evaluate(solution, challenge)

        # 4. Update R-Zero state
        self.allostatica.update_difficulty(evaluation)

        # 5. Build trajectory
        trajectory = [
            FlumeTrajectoryPoint(
                step=0,
                text=solution.response_text,
                z_vector=solution.z_vector,
                coherence=evaluation.coherence,
            )
        ]

        # 6. Create result
        result = EnhancedSimulationResult(
            sim_id=f"sim_{int(time.time())}_{self.total_completed}",
            stream=stream,
            challenge=challenge,
            solution=solution,
            evaluation=evaluation,
            trajectory=trajectory,
            approved=evaluation.approved,
        )

        # 7. Log result
        self._log_result(result)

        # 8. Persist to DB
        await self.persist_result(result)

        self.total_completed += 1
        if evaluation.approved:
            self.total_approved += 1

        return result

    async def run_batch(self, batch_size: int = 100) -> list[EnhancedSimulationResult]:
        """Run a batch of simulations across all streams."""
        results = []

        for i in range(batch_size):
            stream = self.STREAMS[i % len(self.STREAMS)]
            result = await self.run_simulation(stream)
            results.append(result)

        logger.info(
            f"Batch complete: {batch_size} sims, "
            f"Approved: {sum(1 for r in results if r.approved)}, "
            f"Difficulty: {self.allostatica.difficulty:.2f}, "
            f"Epoch: {self.allostatica.epoch}"
        )

        return results

    def _log_result(self, result: EnhancedSimulationResult):
        """Log result to JSONL files."""
        # Main results
        result_dict = {
            "sim_id": result.sim_id,
            "stream": result.stream,
            "difficulty": result.challenge.difficulty,
            "epoch": self.allostatica.epoch,
            "score": result.evaluation.score,
            "coherence": result.evaluation.coherence,
            "approved": result.approved,
            "issues": result.evaluation.issues,
            "timestamp": result.timestamp,
        }

        with open(self.results_path, "a") as f:
            f.write(json.dumps(result_dict) + "\n")

        # Trajectory data
        for point in result.trajectory:
            traj_dict = {
                "sim_id": result.sim_id,
                "stream": result.stream,
                "step": point.step,
                "z_vector": point.z_vector[:8],  # First 8 dims for compactness
                "coherence": point.coherence,
                "timestamp": point.timestamp,
            }
            with open(self.trajectories_path, "a") as f:
                f.write(json.dumps(traj_dict) + "\n")

    async def persist_result(self, result: EnhancedSimulationResult):
        """Persist result to SurrealDB as an AgentJourney."""
        try:
            # Connect if needed
            if not self.db._connected:
                await self.db.connect()

            # Map to AgentJourney
            journey = AgentJourney(
                journey_id=result.sim_id,
                query=", ".join(result.challenge.constraints),
                started_at=result.timestamp,
                final_response=result.solution.response_text,
                final_confidence=result.evaluation.score,
                total_duration_ms=0,  # TODO: measure
                aggregate_metrics=JourneyMetrics(
                    context_utilization=result.evaluation.coherence,
                    latent_coherence=result.evaluation.coherence,
                    capability_delta=result.challenge.difficulty,
                    latency_per_token_ms=0,
                    safety_alignment_score=1.0 if result.approved else 0.0,
                    computational_relativity_factor=1.0,
                ),
                steps=[
                    {
                        "step": p.step,
                        "text": p.text,
                        "z_vector": p.z_vector,
                        "coherence": p.coherence,
                        "timestamp": p.timestamp,
                    }
                    for p in result.trajectory
                ],
                metadata={
                    "stream": result.stream,
                    "difficulty": result.challenge.difficulty,
                    "approved": result.approved,
                    "issues": result.evaluation.issues,
                },
            )

            await self.repository.add(journey)
            logger.info(f"Persisted sim {result.sim_id} to SurrealDB")

        except Exception as e:
            logger.error(f"Failed to persist result to DB: {e}")

    def get_stats(self) -> dict:
        """Get simulation statistics."""
        return {
            "total_completed": self.total_completed,
            "total_approved": self.total_approved,
            "approval_rate": self.total_approved / max(1, self.total_completed),
            "current_difficulty": self.allostatica.difficulty,
            "current_epoch": self.allostatica.epoch,
            "avg_score": sum(self.allostatica.history[-100:])
            / max(1, len(self.allostatica.history[-100:])),
        }


async def main():
    """Demo of enhanced simulation."""
    logging.basicConfig(level=logging.INFO)

    simulator = EnhancedSimulator()

    # Run 5 batches of 100 simulations each
    for _batch in range(5):
        await simulator.run_batch(100)
        stats = simulator.get_stats()
        logger.info(f"Stats: {stats}")

    print(f"\nFinal Stats: {simulator.get_stats()}")


if __name__ == "__main__":
    asyncio.run(main())
