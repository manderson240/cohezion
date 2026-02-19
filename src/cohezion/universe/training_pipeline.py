"""Universe Training Pipeline - End-to-End Agentic Training Environment.

Connects all universe simulation components into a cohesive pipeline:
ScenarioGenerator → NexusDispatch → BioelectricNavigation →
VAE Encoding → CapabilityEvaluation → Ouroboros Recording.
"""

from __future__ import annotations

import logging
import random
import tempfile
from dataclasses import dataclass, field
from typing import cast

import numpy as np

from cohezion.system.ouroboros_recorder import OuroborosRecorder
from cohezion.universe.bioelectric_navigator import BioelectricNavigator
from cohezion.universe.capability_evaluator import (
    CapabilityEvaluator,
    CapabilityProfile,
    CapabilityScore,
)
from cohezion.universe.evo_agent import EVOAgent
from cohezion.universe.nexus_dispatch import NexusScenarioDispatcher
from cohezion.universe.scenarios import ScenarioGenerator, ScenarioType
from cohezion.universe.vae_journey_encoder import VAEJourneyEncoder


logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for a training pipeline run."""

    scenario_count: int = 10
    agent_count: int = 3
    max_concurrent_scenarios: int = 4
    max_steps: int = 50
    difficulty_min: float = 0.1
    difficulty_max: float = 0.8
    seed: int = 42


@dataclass
class MyceliumSignal:
    """Signal emitted to the Mycelium network after pipeline completion."""

    event_type: str
    scenario_count: int
    agent_count: int
    capability_deltas: dict[str, float]
    regressions: list[str] = field(default_factory=list)


def emit_mycelium_signal(signal: MyceliumSignal) -> None:
    """Emit a signal to the Mycelium network (log-based interface).

    Args:
        signal: Signal to emit
    """
    logger.info(
        f"Mycelium signal: {signal.event_type} "
        f"scenarios={signal.scenario_count} agents={signal.agent_count} "
        f"deltas={signal.capability_deltas}"
    )
    if signal.regressions:
        logger.warning(f"Capability regressions: {signal.regressions}")


@dataclass
class TrainingReport:
    """Report from a training pipeline run."""

    scenarios_completed: int
    scenarios_failed: int
    agents_evaluated: int
    agent_profiles: dict[str, CapabilityProfile]
    journey_embeddings: list[np.ndarray]
    recording_id: str | None
    mycelium_signal: MyceliumSignal | None


class UniverseTrainingPipeline:
    """End-to-end agentic training environment pipeline."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        """Initialize pipeline with all components.

        Args:
            config: Training configuration (uses defaults if None)
        """
        self.config = config or TrainingConfig()
        self.rng = random.Random(self.config.seed)  # noqa: S311
        self.generator = ScenarioGenerator(seed=self.config.seed)
        self.dispatcher = NexusScenarioDispatcher()
        self.navigator = BioelectricNavigator()
        self.encoder = VAEJourneyEncoder()
        self.evaluator = CapabilityEvaluator()

        # Use temp dir for recorder to avoid polluting data/
        self._recorder_dir = tempfile.mkdtemp(prefix="ouroboros_")
        self.recorder = OuroborosRecorder(data_dir=self._recorder_dir)

    def run(self) -> TrainingReport:
        """Execute complete training pipeline.

        Returns:
            TrainingReport with results
        """
        # 1. Generate scenarios (cycle through types)
        scenario_types = list(ScenarioType)
        scenarios = [
            self.generator.generate(self.rng.choice(scenario_types))
            for _ in range(self.config.scenario_count)
        ]

        # 2. Create agents
        agents = [
            EVOAgent(agent_id=f"agent-{i}") for i in range(self.config.agent_count)
        ]

        # 3. Start recording
        recording_id = self.recorder.start_recording("training-run")

        # 4. Execute scenarios in batches
        all_scores: dict[str, list[CapabilityScore]] = {a.agent_id: [] for a in agents}
        journey_embeddings: list[np.ndarray] = []
        scenarios_completed = 0
        scenarios_failed = 0

        for batch_start in range(
            0, len(scenarios), self.config.max_concurrent_scenarios
        ):
            batch = scenarios[
                batch_start : batch_start + self.config.max_concurrent_scenarios
            ]

            for scenario in batch:
                # Dispatch to fabric
                dispatch_result = self.dispatcher.dispatch(scenario)

                for agent in agents:
                    try:
                        # Navigate agent through scenario
                        trajectory = self.navigator.navigate_scenario(
                            scenario, agent, max_steps=self.config.max_steps
                        )

                        # Encode journey to 256D
                        traj_obj = cast("list[dict[str, object]]", trajectory)
                        embedding = self.encoder.encode_trajectory_raw(traj_obj)
                        journey_embeddings.append(embedding)

                        # Evaluate capability
                        journey_dicts = self._trajectory_to_journey(traj_obj)
                        score = self.evaluator.evaluate(scenario, journey_dicts)
                        all_scores[agent.agent_id].append(score)

                        # Record to Ouroboros
                        self.recorder.record_event(
                            recording_id,
                            event_type="scenario_complete",
                            data={
                                "agent": agent.agent_id,
                                "fabric": dispatch_result.fabric,
                                "scenario_type": scenario.type.value,
                                "composite_score": score.composite(),
                            },
                        )

                        scenarios_completed += 1

                    except Exception as e:
                        logger.warning(f"Scenario failed for {agent.agent_id}: {e}")
                        scenarios_failed += 1
                        self.recorder.record_divergence(
                            recording_id,
                            divergence_type="scenario_failure",
                            last_good_state={"agent": agent.agent_id},
                            divergent_state={"error": str(e)},
                        )

                    # Reset agent for next scenario
                    from cohezion.universe.engine import AxiomaticState

                    agent.state = AxiomaticState()

        # 5. Aggregate profiles
        agent_profiles: dict[str, CapabilityProfile] = {}
        for agent_id, scores in all_scores.items():
            agent_profiles[agent_id] = CapabilityProfile.from_scores(scores)

        # 6. Emit Mycelium signal
        signal = MyceliumSignal(
            event_type="pipeline_complete",
            scenario_count=scenarios_completed,
            agent_count=len(agents),
            capability_deltas=self._compute_deltas(agent_profiles),
        )
        emit_mycelium_signal(signal)

        return TrainingReport(
            scenarios_completed=scenarios_completed,
            scenarios_failed=scenarios_failed,
            agents_evaluated=len(agents),
            agent_profiles=agent_profiles,
            journey_embeddings=journey_embeddings,
            recording_id=recording_id,
            mycelium_signal=signal,
        )

    def find_similar_journeys(
        self,
        query: np.ndarray,
        embeddings: list[np.ndarray],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """Find similar journeys using cosine similarity.

        Args:
            query: Query embedding (256D)
            embeddings: List of journey embeddings
            top_k: Number of results to return

        Returns:
            List of (index, similarity) tuples sorted by similarity
        """
        similarities: list[tuple[int, float]] = []
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []

        for i, emb in enumerate(embeddings):
            emb_norm = np.linalg.norm(emb)
            if emb_norm == 0:
                continue
            sim = float(np.dot(query, emb) / (query_norm * emb_norm))
            similarities.append((i, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def _trajectory_to_journey(
        self, trajectory: list[dict[str, object]]
    ) -> list[dict[str, float]]:
        """Convert navigator trajectory to evaluator journey format.

        Args:
            trajectory: List of trajectory points from BioelectricNavigator

        Returns:
            List of dicts with x, y, coherence keys for CapabilityEvaluator
        """
        journey: list[dict[str, float]] = []
        for point in trajectory:
            state = point.get("state")
            if isinstance(state, np.ndarray):
                journey.append(
                    {
                        "x": float(state[0]),
                        "y": float(state[1]),
                        "coherence": float(np.mean(state[4:11])),  # HIHO dims average
                    }
                )
            else:
                journey.append({"x": 0.0, "y": 0.0, "coherence": 0.5})
        return journey

    def _compute_deltas(
        self, profiles: dict[str, CapabilityProfile]
    ) -> dict[str, float]:
        """Compute capability deltas across agents.

        Args:
            profiles: Per-agent capability profiles

        Returns:
            Mean capability scores as deltas
        """
        if not profiles:
            return {}

        totals: dict[str, float] = {
            "task_completion": 0.0,
            "coherence_maintenance": 0.0,
            "context_retention": 0.0,
            "ambiguity_handling": 0.0,
            "interruption_recovery": 0.0,
            "judgment_quality": 0.0,
        }

        for profile in profiles.values():
            totals["task_completion"] += profile.task_completion
            totals["coherence_maintenance"] += profile.coherence_maintenance
            totals["context_retention"] += profile.context_retention
            totals["ambiguity_handling"] += profile.ambiguity_handling
            totals["interruption_recovery"] += profile.interruption_recovery
            totals["judgment_quality"] += profile.judgment_quality

        n = len(profiles)
        return {k: v / n for k, v in totals.items()}
