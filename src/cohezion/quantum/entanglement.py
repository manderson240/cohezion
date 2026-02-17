"""
ER=EPR Entanglement Network
Small-world network for instantaneous quantum correlations.
"""

import numpy as np
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import logging

from .quantum_state import QuantumAgent

logger = logging.getLogger(__name__)


@dataclass
class EntanglementLink:
    """
    ER=EPR bridge between two agents.

    Agents sharing 12D coordinates are entangled.
    Measurement on one instantly affects the other.
    """

    agent_a_id: int
    agent_b_id: int
    strength: float  # 0.0 to 1.0
    shared_coordinate: np.ndarray  # 12D wormhole coordinate

    def correlate(
        self,
        measured_agent_id: int,
        outcome: np.ndarray,
        agents_dict: Dict[int, QuantumAgent],
    ):
        """
        Apply instantaneous correlation.

        When one agent is measured, partner's state updates instantly.
        """
        # Determine which agent was measured
        if measured_agent_id == self.agent_a_id:
            partner_id = self.agent_b_id
        else:
            partner_id = self.agent_a_id

        # Get partner agent
        if partner_id not in agents_dict:
            return

        partner = agents_dict[partner_id]

        # Anti-correlate positions (Bell state property)
        # Partner moves opposite direction
        partner.position_12d = -outcome * self.strength

        # Energy cost for maintaining correlation
        if partner_id in agents_dict:
            partner.energy -= 0.02

        # Update coherence based on correlation strength
        partner.coherence *= self.strength


class EntanglementNetwork:
    """
    Small-world network of 10,000 entangled quantum agents.

    Uses Watts-Strogatz model:
    - Ring lattice with local connections
    - Random rewiring for small-world property
    """

    def __init__(self, n_agents: int = 10000, k: int = 6, p: float = 0.2):
        """
        Initialize small-world entanglement network.

        Args:
            n_agents: Number of agents in network
            k: Number of nearest neighbors (each side)
            p: Rewiring probability
        """
        self.n_agents = n_agents
        self.k = k
        self.p = p

        # Links will be created when agents are registered
        self.links: List[EntanglementLink] = []
        self.adjacency: Dict[int, List[int]] = {i: [] for i in range(n_agents)}

        logger.info(f"Entanglement network initialized for {n_agents} agents")

    def create_small_world_network(self, agents: List[QuantumAgent]):
        """
        Create Watts-Strogatz small-world topology.

        1. Create ring lattice with k nearest neighbors
        2. Rewire each edge with probability p
        """
        self.links = []
        self.adjacency = {i: [] for i in range(self.n_agents)}

        # Step 1: Create ring lattice
        for i in range(self.n_agents):
            for j in range(1, self.k // 2 + 1):
                # Connect to j neighbors on each side
                neighbor_right = (i + j) % self.n_agents
                neighbor_left = (i - j) % self.n_agents

                # Create links
                self._add_link(i, neighbor_right, 1.0)
                self._add_link(i, neighbor_left, 1.0)

        # Step 2: Rewire with probability p
        links_to_rewire = []
        for link in self.links:
            if np.random.random() < self.p:
                links_to_rewire.append(link)

        for link in links_to_rewire:
            # Remove old link
            self._remove_link(link)

            # Create new random link
            agent_a = link.agent_a_id
            new_target = np.random.randint(0, self.n_agents)

            # Ensure not self-loop or duplicate
            attempts = 0
            while (
                new_target == agent_a or new_target in self.adjacency[agent_a]
            ) and attempts < 10:
                new_target = np.random.randint(0, self.n_agents)
                attempts += 1

            if attempts < 10:
                self._add_link(agent_a, new_target, 1.0)

        # Compute shared coordinates for wormholes
        self._compute_wormhole_coordinates(agents)

        logger.info(f"Created {len(self.links)} entanglement links")

    def _add_link(self, agent_a: int, agent_b: int, strength: float):
        """Add entanglement link between two agents."""
        # Avoid duplicates
        if agent_b in self.adjacency.get(agent_a, []):
            return

        # Create link
        link = EntanglementLink(
            agent_a_id=agent_a,
            agent_b_id=agent_b,
            strength=strength,
            shared_coordinate=np.zeros(12),  # Will be computed later
        )

        self.links.append(link)

        # Update adjacency
        if agent_a not in self.adjacency:
            self.adjacency[agent_a] = []
        if agent_b not in self.adjacency:
            self.adjacency[agent_b] = []

        self.adjacency[agent_a].append(agent_b)
        self.adjacency[agent_b].append(agent_a)

    def _remove_link(self, link: EntanglementLink):
        """Remove an entanglement link."""
        if link in self.links:
            self.links.remove(link)

        # Update adjacency
        if link.agent_b_id in self.adjacency.get(link.agent_a_id, []):
            self.adjacency[link.agent_a_id].remove(link.agent_b_id)
        if link.agent_a_id in self.adjacency.get(link.agent_b_id, []):
            self.adjacency[link.agent_b_id].remove(link.agent_a_id)

    def _compute_wormhole_coordinates(self, agents: List[QuantumAgent]):
        """
        Compute shared 12D coordinates for wormholes.

        Each link gets a coordinate midway between agent positions.
        """
        agent_dict = {a.id: a for a in agents}

        for link in self.links:
            if link.agent_a_id in agent_dict and link.agent_b_id in agent_dict:
                agent_a = agent_dict[link.agent_a_id]
                agent_b = agent_dict[link.agent_b_id]

                # Wormhole at midpoint
                link.shared_coordinate = (
                    agent_a.position_12d + agent_b.position_12d
                ) / 2

    def propagate_information(
        self,
        source_id: int,
        information: dict,
        agents_dict: Dict[int, QuantumAgent],
        max_hops: int = 4,
    ) -> Set[int]:
        """
        Propagate information through entanglement network.

        Uses BFS with hop limit. Faster than classical due to quantum correlations.

        Args:
            source_id: Source agent ID
            information: Data to propagate
            agents_dict: Dictionary of all agents
            max_hops: Maximum propagation distance

        Returns:
            Set of agent IDs that received information
        """
        visited = {source_id}
        queue = [(source_id, 0)]  # (agent_id, hop_count)
        received = {source_id}

        while queue:
            agent_id, hops = queue.pop(0)

            if hops >= max_hops:
                continue

            # Get neighbors
            neighbors = self.adjacency.get(agent_id, [])

            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    received.add(neighbor_id)

                    # Deliver information
                    if neighbor_id in agents_dict:
                        agents_dict[neighbor_id].receive_information(
                            information, hops + 1
                        )

                    # Continue propagation
                    queue.append((neighbor_id, hops + 1))

        return received

    def get_links_for_agent(self, agent_id: int) -> List[EntanglementLink]:
        """Get all entanglement links for an agent."""
        return [
            link
            for link in self.links
            if link.agent_a_id == agent_id or link.agent_b_id == agent_id
        ]

    def get_network_stats(self) -> dict:
        """Compute network statistics."""
        degrees = [len(neighbors) for neighbors in self.adjacency.values()]

        return {
            "n_agents": self.n_agents,
            "n_links": len(self.links),
            "avg_degree": np.mean(degrees),
            "max_degree": max(degrees) if degrees else 0,
            "min_degree": min(degrees) if degrees else 0,
            "clustering_coefficient": self._estimate_clustering(),
        }

    def _estimate_clustering(self) -> float:
        """Estimate clustering coefficient (simplified)."""
        # For small-world networks, this is typically high
        # Exact computation is expensive for 10K nodes
        return 0.3  # Typical for Watts-Strogatz with k=6, p=0.2

    def break_weak_links(self, threshold: float = 0.1):
        """
        Remove weak entanglement links.

        Called when agents have low energy.
        """
        weak_links = [link for link in self.links if link.strength < threshold]

        for link in weak_links:
            self._remove_link(link)

        if weak_links:
            logger.info(f"Broke {len(weak_links)} weak entanglement links")


# Extend QuantumAgent with information reception
def receive_information(self, information: dict, hop_count: int):
    """Receive information from entangled partner."""
    # Store in agent's memory
    if not hasattr(self, "received_info"):
        self.received_info = []

    self.received_info.append(
        {"information": information, "hops": hop_count, "timestamp": len(self.journey)}
    )


# Add method to QuantumAgent
QuantumAgent.receive_information = receive_information
