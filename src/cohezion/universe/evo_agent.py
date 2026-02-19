"""EVO Agent Model - Exotic Vacuum Objects navigating morphospace.

Agents are modeled as charge clusters maintaining HIHO (0.5) coherence stability
through bioelectric navigation in 12D morphospace.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cohezion.universe.engine import AxiomaticState


logger = logging.getLogger(__name__)

# HIHO target coherence
HIHO_TARGET = 0.5
HIHO_DRIFT_RATE = 0.1  # How quickly agent moves toward HIHO


@dataclass
class EVOAgent:
    """EVO Agent - Exotic Vacuum Object navigating morphospace.

    Agents maintain coherence through the HIHO (Half-In-Half-Out) stability
    mechanism, where optimal coherence is achieved at 0.5 overlap across dimensions.
    """

    agent_id: str
    state: AxiomaticState = field(default_factory=AxiomaticState)
    coherence_history: list[float] = field(default_factory=list)
    memory_buffer: list[dict[str, Any]] = field(default_factory=list)
    memory_capacity: int = 10

    def __post_init__(self):
        """Initialize agent with initial coherence."""
        if not self.coherence_history:
            self.coherence_history.append(self.state.coherence_score())

    def perceive(self, environment: dict[str, Any]) -> dict[str, Any]:
        """Perceive local environment and agent's own state.

        Args:
            environment: Environment data (local field, nearby agents, etc.)

        Returns:
            Perception dict containing state and environment info
        """
        perception = {
            "state": self.state,
            "coherence": self.state.coherence_score(),
            **environment,  # Include all environment data
        }
        return perception

    def decide(self, perception: dict[str, Any]) -> dict[str, Any]:
        """Decide on action based on perception.

        Uses bioelectric gradient toward HIHO target (0.5) for decision-making.

        Args:
            perception: Perception from perceive()

        Returns:
            Action dict with action_vector (12D)
        """
        current_state = perception["state"]
        coherence = perception.get("coherence", current_state.coherence_score())

        # Compute action vector: gradient toward HIHO (0.5) in all dimensions
        action_vector = []
        for dim_value in [
            current_state.physics,
            current_state.biology,
            current_state.logic,
            current_state.quantum,
            current_state.field,
            current_state.control,
            current_state.novelty,
        ]:
            # Move toward 0.5 with drift rate
            delta = (HIHO_TARGET - dim_value) * HIHO_DRIFT_RATE
            action_vector.append(delta)

        # Spatial dimensions: small random drift
        action_vector = (
            [np.random.uniform(-0.01, 0.01)] * 3
            + [0.0]  # spatial x, y, z  # temporal (no action)
            + action_vector  # HIHO-driven dimensions
            + [0.0]  # precipitation (no action)
        )

        return {"action_vector": action_vector}

    def act(self, action: dict[str, Any]) -> None:
        """Apply action to update agent state.

        Args:
            action: Action dict from decide()
        """
        action_vector = action["action_vector"]

        # Update state by adding action vector
        current = self.to_numpy()
        updated = current + np.array(action_vector)

        # Clamp values to valid ranges
        # Spatial: unbounded, Temporal: unbounded
        # Dimensions 4-10 (physics-novelty): [0, 1]
        # Precipitation: unbounded
        for i in range(4, 11):
            updated[i] = np.clip(updated[i], 0.0, 1.0)

        self.update_from_numpy(updated)

        # Record coherence
        self.coherence_history.append(self.state.coherence_score())

    def remember(self, interaction: dict[str, Any]) -> None:
        """Store interaction in memory buffer.

        Args:
            interaction: Interaction data to remember
        """
        self.memory_buffer.append(interaction)
        # Enforce capacity limit
        if len(self.memory_buffer) > self.memory_capacity:
            self.memory_buffer = self.memory_buffer[-self.memory_capacity :]

    def to_numpy(self) -> np.ndarray:
        """Convert AxiomaticState to numpy array.

        Returns:
            12D numpy array
        """
        return np.array(self.state.to_vector(), dtype=float)

    def update_from_numpy(self, arr: np.ndarray) -> None:
        """Update AxiomaticState from numpy array.

        Args:
            arr: 12D numpy array
        """
        self.state = AxiomaticState.from_vector(arr.tolist())


@dataclass
class EVOPopulation:
    """Population of EVO agents with inter-agent field interactions."""

    num_agents: int
    agents: list[EVOAgent] = field(default_factory=list)
    field_coupling_strength: float = 0.01  # How strongly agents influence each other

    def __post_init__(self):
        """Initialize population with agents."""
        if not self.agents:
            self.agents = [
                EVOAgent(agent_id=f"evo-{i}", state=AxiomaticState())
                for i in range(self.num_agents)
            ]

    def step(self) -> None:
        """Execute one step of population dynamics with field interactions."""
        # Compute field influences
        field_influences = self._compute_field_influences()

        # Each agent perceives, decides, and acts
        for i, agent in enumerate(self.agents):
            # Environment includes field influence from other agents
            environment = {
                "local_field": field_influences[i],
                "nearby_agents": self._get_nearby_agents(agent),
            }

            perception = agent.perceive(environment)
            action = agent.decide(perception)

            # Add field influence to action
            action_vector = np.array(action["action_vector"])
            field_vector = np.array(field_influences[i])
            combined_action = (
                action_vector + field_vector * self.field_coupling_strength
            )

            agent.act({"action_vector": combined_action.tolist()})

    def _compute_field_influences(self) -> list[list[float]]:
        """Compute field influence on each agent from all other agents.

        Returns:
            List of 12D influence vectors, one per agent
        """
        influences = []
        for i, agent in enumerate(self.agents):
            # Sum influence from all other agents
            influence = np.zeros(12)
            for j, other in enumerate(self.agents):
                if i == j:
                    continue
                # Simple distance-based influence
                distance = np.linalg.norm(agent.to_numpy() - other.to_numpy())
                if distance > 0:
                    direction = (other.to_numpy() - agent.to_numpy()) / distance
                    # Inverse square law
                    strength = 1.0 / (distance**2 + 1.0)
                    influence += direction * strength

            influences.append(influence.tolist())

        return influences

    def _get_nearby_agents(self, agent: EVOAgent) -> list[str]:
        """Get IDs of agents near the given agent.

        Args:
            agent: Reference agent

        Returns:
            List of nearby agent IDs
        """
        nearby = []
        agent_pos = agent.to_numpy()
        for other in self.agents:
            if other.agent_id == agent.agent_id:
                continue
            other_pos = other.to_numpy()
            distance = np.linalg.norm(agent_pos - other_pos)
            if distance < 1.0:  # Within unit distance
                nearby.append(other.agent_id)
        return nearby

    def get_agent(self, agent_id: str) -> EVOAgent | None:
        """Retrieve agent by ID.

        Args:
            agent_id: Agent ID to retrieve

        Returns:
            Agent if found, None otherwise
        """
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
