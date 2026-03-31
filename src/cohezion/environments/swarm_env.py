"""SwarmEnv — Multi-agent environment on the 12D manifold.

N agents navigate the same 12D Riemannian manifold simultaneously.
Agents interact through gauge field coupling: one agent's motion
generates curvature that affects other agents' dynamics.

Cooperative objective: all agents converge to HIHO collectively.
Each agent's reward depends on BOTH individual and global coherence.

The topology of agent interactions evolves in real-time — the
TopologicalRouter tracks cluster formation and loop structure
to optimize task routing.

Compatible with PettingZoo's parallel API pattern:
    env = SwarmEnv(n_agents=4)
    observations, infos = env.reset()
    while not all_done:
        actions = {agent: policy(obs) for agent, obs in observations.items()}
        observations, rewards, terminateds, truncateds, infos = env.step(actions)

References:
    - PettingZoo parallel API: https://pettingzoo.farama.org/
    - [2512.08296] Towards a Science of Scaling Agent Systems
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from cohezion.physics.fiber_bundle import FiberBundle
from cohezion.physics.gauge_theory import FourFabricGauge
from cohezion.physics.lagrangian import LagrangianDynamics, hiho_potential
from cohezion.physics.riemannian_metric import fabric_block_metric
from cohezion.physics.spinor import SpinorState

logger = logging.getLogger(__name__)


class SwarmEnv:
    """Multi-agent 12D manifold environment with gauge field coupling.

    Parameters
    ----------
    n_agents : int
        Number of agents (default: 4).
    dim : int
        Manifold dimension (default: 12).
    max_steps : int
        Maximum steps per episode (default: 500).
    coupling_strength : float
        How strongly agents' gauge fields affect each other (default: 0.1).
    """

    def __init__(
        self,
        n_agents: int = 4,
        dim: int = 12,
        max_steps: int = 500,
        dt: float = 0.01,
        damping: float = 0.1,
        coupling_strength: float = 0.1,
        seed: int | None = None,
    ) -> None:
        self.n_agents = n_agents
        self.dim = dim
        self.max_steps = max_steps
        self.dt = dt
        self.coupling_strength = coupling_strength

        # Agent IDs
        self.possible_agents = [f"agent_{i}" for i in range(n_agents)]
        self.agents = list(self.possible_agents)

        # Physics
        self._metric = fabric_block_metric(dim)
        self._potential = hiho_potential(dim)
        self._dynamics = LagrangianDynamics(self._metric, self._potential, damping=damping)
        self._fiber_bundle = FiberBundle(dim)
        self._gauge = FourFabricGauge()

        # State per agent
        self._positions: dict[str, np.ndarray] = {}
        self._velocities: dict[str, np.ndarray] = {}
        self._step_count = 0

        self._rng = np.random.default_rng(seed)

    def reset(self, seed: int | None = None) -> tuple[dict[str, np.ndarray], dict[str, dict]]:
        """Reset all agents to random positions.

        Returns (observations, infos) dicts keyed by agent ID.
        """
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self.agents = list(self.possible_agents)
        self._step_count = 0

        for agent_id in self.agents:
            self._positions[agent_id] = self._rng.uniform(0.2, 0.8, self.dim).astype(np.float32)
            self._velocities[agent_id] = self._rng.normal(0, 0.02, self.dim).astype(np.float32)

        return self._get_all_obs(), self._get_all_info()

    def step(
        self, actions: dict[str, np.ndarray]
    ) -> tuple[
        dict[str, np.ndarray],
        dict[str, float],
        dict[str, bool],
        dict[str, bool],
        dict[str, dict],
    ]:
        """Execute one step for all agents simultaneously.

        Parameters
        ----------
        actions : dict mapping agent_id → 12D action vector.

        Returns (observations, rewards, terminateds, truncateds, infos).
        """
        self._step_count += 1

        # Compute gauge coupling field (sum of all agents' gauge fields)
        coupling_field = self._compute_coupling_field()

        # Evolve each agent
        rewards = {}
        for agent_id in self.agents:
            action = np.asarray(actions.get(agent_id, np.zeros(self.dim)), dtype=np.float32)
            action = action.clip(-0.5, 0.5)

            # Apply action + gauge coupling from other agents
            coupled_action = action + coupling_field * self.coupling_strength
            self._velocities[agent_id] = self._velocities[agent_id] * 0.9 + coupled_action * 0.1

            # Lagrangian evolution
            new_pos, new_vel = self._dynamics.step_verlet(
                self._positions[agent_id].astype(np.float64),
                self._velocities[agent_id].astype(np.float64),
                self.dt,
            )
            self._positions[agent_id] = np.clip(new_pos, -1.5, 2.0).astype(np.float32)
            self._velocities[agent_id] = new_vel.astype(np.float32)

            # Individual + collective reward
            rewards[agent_id] = self._compute_agent_reward(agent_id)

        # Termination: all agents at HIHO
        global_deviation = self._compute_global_hiho_deviation()
        all_at_hiho = global_deviation < 0.02

        terminateds = {a: all_at_hiho for a in self.agents}
        truncateds = {a: self._step_count >= self.max_steps for a in self.agents}

        return (
            self._get_all_obs(),
            rewards,
            terminateds,
            truncateds,
            self._get_all_info(),
        )

    def _compute_coupling_field(self) -> np.ndarray:
        """Compute the mean gauge field from all agents.

        Each agent's position generates a gauge field. The coupling
        is the mean field — agents near HIHO contribute less coupling
        (flat connection), while agents far from HIHO contribute more.
        """
        if not self.agents:
            return np.zeros(self.dim, dtype=np.float32)

        total_field = np.zeros(self.dim, dtype=np.float64)
        for agent_id in self.agents:
            deviation = self._positions[agent_id].astype(np.float64) - 0.5
            total_field += deviation

        return (total_field / len(self.agents)).astype(np.float32)

    def _compute_agent_reward(self, agent_id: str) -> float:
        """Reward = individual coherence + collective coherence bonus."""
        pos = self._positions[agent_id]
        brane = pos[4:11]

        # Individual coherence
        individual_var = float(np.mean((brane - 0.5) ** 2))
        individual_coherence = 1.0 - min(individual_var * 4, 1.0)

        # Collective coherence (mean across all agents)
        collective_coherence = 1.0 - self._compute_global_hiho_deviation() * 4

        return 0.5 * individual_coherence + 0.5 * max(collective_coherence, 0)

    def _compute_global_hiho_deviation(self) -> float:
        """Mean HIHO deviation across all agents."""
        if not self.agents:
            return 1.0
        deviations = []
        for agent_id in self.agents:
            brane = self._positions[agent_id][4:11]
            deviations.append(float(np.mean(np.abs(brane - 0.5))))
        return float(np.mean(deviations))

    def _get_obs(self, agent_id: str) -> np.ndarray:
        """19D observation for a single agent."""
        pos = self._positions[agent_id]

        spinor = SpinorState.from_coherence_values(
            float(np.clip(pos[6], 0, 1)),
            float(np.clip(pos[7], 0, 1)),
        )
        bloch = spinor.bloch_vector.astype(np.float32)
        fiber_base = self._fiber_bundle.project_to_base(pos.astype(np.float64)).astype(np.float32)

        return np.concatenate([pos, bloch, fiber_base])

    def _get_all_obs(self) -> dict[str, np.ndarray]:
        return {a: self._get_obs(a) for a in self.agents}

    def _get_all_info(self) -> dict[str, dict]:
        global_dev = self._compute_global_hiho_deviation()
        return {
            a: {
                "step": self._step_count,
                "global_hiho_deviation": global_dev,
                "n_agents": len(self.agents),
            }
            for a in self.agents
        }


__all__ = ["SwarmEnv"]

# Register with Gymnasium for discoverability (matching ManifoldEnv pattern)
try:
    import gymnasium as gym

    gym.register(
        id="Cohezion/SwarmEnv-v0",
        entry_point="cohezion.environments.swarm_env:SwarmEnv",
        max_episode_steps=500,
    )
except ImportError:
    pass  # gymnasium not installed
