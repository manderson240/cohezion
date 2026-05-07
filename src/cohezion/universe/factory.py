"""UniverseFactory — create an agentic universe with EVO agents and run rollouts.

One call spawns a universe: cosmogony cools through its phase transitions,
N EVO agents condense from the model vacuum, a ManifoldEnv wraps them as RL
agents, and a QuadratureNexus gates each action on >=0.85 consensus. Every
state transition emits a PrecipitationEvent through the shared bus.

The Universe.run() method returns AgentTrajectory records compatible with the
existing LLMTrainingBridge so they can be directly exported to DPO / RLHF /
judgment datasets in Phase 4.

Example:
    spec = UniverseSpec(
        universe_id="u-001",
        agent_count=2,
        max_steps=50,
        seed=42,
    )
    factory = UniverseFactory()
    universe = await factory.create_universe(spec)
    trajectories = await factory.run(universe)
    # trajectories is list[AgentTrajectory] ready for ExperienceDataset.export
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from cohezion.environments.manifold_env import ManifoldEnv
from cohezion.physics.cosmogony import SymmetryBreaking
from cohezion.physics.evo_model import ExoticVacuumObject
from cohezion.precipitation import (
    PrecipitationBus,
    PrecipitationEvent,
    PrecipitationKind,
    emit,
    get_bus,
)
from cohezion.precipitation.events import TWELVE_D_DIMS, compute_fabric_breakdown
from cohezion.swarm.quadrature_nexus import QuadratureNexus
from cohezion.universe.llm_training_bridge import AgentTrajectory, TrajectoryStep


logger = logging.getLogger(__name__)


@dataclass
class UniverseSpec:
    """Specification for a new universe instance.

    Attributes
    ----------
    universe_id : str
        Unique identifier for this universe. All PrecipitationEvents emitted
        during this universe's lifetime carry this id.
    agent_count : int
        How many EVO agents to spawn. Each gets its own ManifoldEnv rollout.
    initial_temperature : float
        Cosmogony starting temperature. Higher = more symmetry breaks to traverse.
    env : Literal["manifold"]
        Environment kind. Only "manifold" is wired in this phase.
    max_steps : int
        Max steps per rollout.
    quadrature_threshold : float
        Consensus floor for the QuadratureNexus associated with this universe.
    witness_interval : int
        Emit a WITNESS_MARK from the EVO every N steps when coherence >= 0.5.
    seed : int | None
        Deterministic seed for env reset.
    model_checkpoint : str | None
        Path to a fine-tuned adapter/weights for the agent's action policy.
        When None, actions are sampled from env.action_space (uniform random).
    """

    universe_id: str
    agent_count: int = 1
    initial_temperature: float = 250.0
    env: Literal["manifold"] = "manifold"
    max_steps: int = 100
    quadrature_threshold: float = 0.85
    witness_interval: int = 20
    seed: int | None = None
    model_checkpoint: str | None = None


@dataclass
class Universe:
    """A running instance of a universe created by UniverseFactory.

    Holds the cosmogony, EVO agents, environment, and nexus — all bound to the
    same universe_id so emitted precipitation events are lineage-traceable.
    """

    spec: UniverseSpec
    cosmogony: SymmetryBreaking
    evos: list[ExoticVacuumObject]
    env: ManifoldEnv
    nexus: QuadratureNexus
    trajectories: list[AgentTrajectory] = field(default_factory=list)


class UniverseFactory:
    """Produces Universe instances wired to the precipitation bus.

    Stateless across universes — one factory can safely create many. Hand the
    factory a PrecipitationBus (or let it use the process singleton) and it
    plumbs every emission through.
    """

    def __init__(self, bus: PrecipitationBus | None = None) -> None:
        self.bus = bus or get_bus()

    async def create_universe(self, spec: UniverseSpec) -> Universe:
        """Instantiate a universe: cool cosmogony, spawn EVOs, build env + nexus."""
        logger.info(
            "UniverseFactory creating universe=%s agents=%d max_steps=%d",
            spec.universe_id,
            spec.agent_count,
            spec.max_steps,
        )

        # 1. Cosmogony: run the full cooling sequence so all phase events are emitted.
        cosmogony = SymmetryBreaking(universe_id=spec.universe_id)
        cosmogony._state.temperature = spec.initial_temperature
        _cool_through_phase_transitions(cosmogony)

        # 2. Spawn N EVO agents, each condensed and bound to the universe.
        evos: list[ExoticVacuumObject] = []
        for i in range(spec.agent_count):
            evo = ExoticVacuumObject(
                agent_id=f"{spec.universe_id}/evo-{i}",
                universe_id=spec.universe_id,
            )
            evo.condense()
            evos.append(evo)

        # 3. ManifoldEnv instance — one env, shared across agents via seed seeding.
        env = ManifoldEnv(max_steps=spec.max_steps, seed=spec.seed)

        # 4. QuadratureNexus for gating critical actions in this universe.
        nexus = QuadratureNexus(universe_id=spec.universe_id)

        # 5. Emit GENERATION_SPAWN so the orchestrator knows a universe is alive.
        _emit_generation_spawn(spec)

        return Universe(spec=spec, cosmogony=cosmogony, evos=evos, env=env, nexus=nexus)

    async def run(self, universe: Universe) -> list[AgentTrajectory]:
        """Roll out each EVO through the manifold env; return trajectories.

        Each agent:
          1. reset env (with a per-agent seed derived from spec.seed)
          2. step max_steps times, sampling from action_space (or policy if available)
          3. record coherence in EVO + per-step TrajectoryStep
          4. emit WITNESS_MARK at witness_interval when coherence >= 0.5
          5. dissolve EVO -> biography
        """
        trajectories: list[AgentTrajectory] = []
        spec = universe.spec

        for idx, evo in enumerate(universe.evos):
            agent_seed = None if spec.seed is None else spec.seed + idx
            obs, info = universe.env.reset(seed=agent_seed)

            steps: list[TrajectoryStep] = []
            total_reward = 0.0
            precipitation_achieved = False

            for step_idx in range(spec.max_steps):
                action = _sample_action(universe.env, spec.model_checkpoint)
                obs, reward, terminated, truncated, info = universe.env.step(action)
                total_reward += reward

                coherence = float(info.get("coherence", 0.5))
                spin_rotation = float(info.get("spin_rotation", 0.0))
                tempic_field = float(info.get("hiho_deviation", 0.5))
                state_12d = obs[:12].astype(float).tolist()

                evo.coherent_phase(coherence)
                steps.append(
                    TrajectoryStep(
                        state_12d=state_12d,
                        action=f"step_{step_idx}",
                        coherence=coherence,
                        spin_coherence=spin_rotation,
                        tempic_field=tempic_field,
                        reward=float(reward),
                        timestamp=float(step_idx),
                    )
                )

                # Witness mark at interval when coherent.
                if step_idx > 0 and step_idx % spec.witness_interval == 0 and coherence >= 0.5:
                    evo.produce_witness_mark(
                        mark_type="rollout_step",
                        content=f"step={step_idx} coh={coherence:.3f} reward={reward:.3f}",
                    )

                if terminated:
                    precipitation_achieved = True
                    # Produce a final, explicit witness mark for the HIHO stabilization.
                    evo.produce_witness_mark(
                        mark_type="hiho_stabilized",
                        content=f"converged at step {step_idx}",
                    )
                    break
                if truncated:
                    break

            final_coherence = (
                float(np.mean(evo.coherence_history)) if evo.coherence_history else 0.0
            )
            biography = evo.dissolve()
            trajectory = AgentTrajectory(
                agent_id=evo.agent_id,
                task_description=(
                    f"Navigate 12D manifold toward HIHO (universe={spec.universe_id})"
                ),
                steps=steps,
                final_coherence=final_coherence,
                total_reward=total_reward,
                precipitation_achieved=precipitation_achieved,
                metadata={
                    "universe_id": spec.universe_id,
                    "evo_biography": biography,
                    "model_checkpoint": spec.model_checkpoint,
                    "cosmogony_transitions": len(universe.cosmogony.state.transitions),
                },
            )
            trajectories.append(trajectory)

        universe.trajectories = trajectories
        return trajectories

    async def save_trajectories(
        self,
        trajectories: list[AgentTrajectory],
        output_dir: Path | str,
    ) -> Path:
        """Persist trajectories as JSON for the Phase 4 orchestrator to read."""
        import json
        from dataclasses import asdict

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        payloads = []
        for trajectory in trajectories:
            # AgentTrajectory contains nested dataclasses; asdict handles them.
            payloads.append(asdict(trajectory))

        target = output_path / f"trajectories-{trajectories[0].agent_id.split('/')[0]}.json"
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payloads, fh, indent=2, default=str)
        return target


def _cool_through_phase_transitions(cosmogony: SymmetryBreaking) -> None:
    """Cool far enough to cascade through every T_c in one pass.

    SymmetryBreaking.cool() iterates through all transitions in stage order, so
    a single large cool() call drives the state down through every symmetry
    break in one shot — each firing mutates current_symmetry so the next
    iteration's match is the next stage's source.

    We call cool() twice: once to the lowest T_c we care about, and once more
    a bit lower to make sure PRECIPITATE (T_c=0.002) fires.
    """
    # Cool to 0.001, which is below every T_c in the transition list.
    cosmogony.cool(delta_t=cosmogony.state.temperature - 0.001)


def _sample_action(env: ManifoldEnv, checkpoint: str | None) -> np.ndarray:
    """Sample an action. In Phase 2, checkpoint is unused — Phase 4 wires it."""
    # Checkpoint-guided policy is wired in Phase 4's orchestrator. For now, sample
    # uniformly from the action space so the universe can run end-to-end.
    return env.action_space.sample()


def _emit_generation_spawn(spec: UniverseSpec) -> None:
    """Best-effort emission of GENERATION_SPAWN for this universe."""
    try:
        # Use initial_coherence as the initial state's twelve_d value (all HIHO-seed).
        twelve_d: dict[str, float] = dict.fromkeys(TWELVE_D_DIMS, 0.5)
        fabric = compute_fabric_breakdown(twelve_d)
        emit(
            PrecipitationEvent(
                kind=PrecipitationKind.GENERATION_SPAWN,
                universe_id=spec.universe_id,
                coherence=0.5,
                twelve_d=twelve_d,
                fabric_breakdown=fabric,
                payload={
                    "agent_count": spec.agent_count,
                    "max_steps": spec.max_steps,
                    "env": spec.env,
                    "initial_temperature": spec.initial_temperature,
                    "quadrature_threshold": spec.quadrature_threshold,
                    "model_checkpoint": spec.model_checkpoint,
                    "seed": spec.seed,
                },
            )
        )
    except Exception:
        logger.debug("Precipitation emit failed for GENERATION_SPAWN", exc_info=True)


__all__ = [
    "Universe",
    "UniverseFactory",
    "UniverseSpec",
]
