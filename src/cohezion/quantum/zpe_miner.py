"""
Zero Point Energy Mining
Extract computational energy from FLUME latent vacuum.
"""

import torch
import numpy as np
from typing import Dict
import logging

from .quantum_state import QuantumAgent

logger = logging.getLogger(__name__)


class ZPEMiner:
    """
    Extract energy from unused dimensions of FLUME latent space.

    FLUME: 256D latent space
    Used: 12D (projected trajectory space)
    Vacuum: 244 dimensions of "unused" space with random fluctuations
    """

    def __init__(
        self,
        initial_vacuum: float = 100000.0,
        mining_rate: float = 0.01,
        extraction_efficiency: float = 0.5,
        regeneration_rate: float = 0.001,
    ):
        """
        Initialize ZPE mining system.

        Args:
            initial_vacuum: Initial vacuum energy pool
            mining_rate: Base rate of energy extraction
            extraction_efficiency: Efficiency factor (0.0 to 1.0)
            regeneration_rate: Vacuum self-healing rate
        """
        self.total_vacuum_energy = initial_vacuum
        self.extracted_energy_total = 0.0

        # Human-tweakable parameters
        self.mining_rate = mining_rate
        self.extraction_efficiency = extraction_efficiency
        self.regeneration_rate = regeneration_rate

        # Dimensions
        self.used_dims = 12
        self.total_dims = 256
        self.vacuum_dims = list(range(12, 256))  # 244 dimensions

        # Thresholds
        self.depletion_threshold = 1000.0
        self.critical_threshold = 100.0

        logger.info(
            f"ZPE mining initialized: {self.total_vacuum_energy:.0f} units available"
        )

    def mine_energy(self, agent: QuantumAgent) -> float:
        """
        Extract energy from latent vacuum for an agent.

        Args:
            agent: Agent to receive energy

        Returns:
            Amount of energy extracted
        """
        # Check if vacuum is depleted
        if self.total_vacuum_energy < self.critical_threshold:
            return 0.0

        # Sample vacuum fluctuations
        vacuum_sample = torch.randn(len(self.vacuum_dims))

        # Convert to probability distribution
        probs = torch.softmax(vacuum_sample, dim=0)

        # Compute informational entropy ("energy content")
        entropy = -torch.sum(probs * torch.log(probs + 1e-10))

        # Convert to energy
        energy_extracted = (
            entropy.item() * self.mining_rate * self.extraction_efficiency
        )

        # Cap extraction to not deplete too fast
        max_extract = self.total_vacuum_energy * 0.001  # Max 0.1% per extraction
        energy_extracted = min(energy_extracted, max_extract)

        # Add to agent (up to max)
        agent.mine_zpe(energy_extracted)

        # Deplete vacuum
        self.total_vacuum_energy -= energy_extracted
        self.extracted_energy_total += energy_extracted

        # Regenerate vacuum (slow self-healing)
        self.total_vacuum_energy += self.regeneration_rate

        return energy_extracted

    def mine_for_all_agents(self, agents) -> Dict[int, float]:
        """
        Mine energy for all agents in one batch.

        Args:
            agents: List of QuantumAgent

        Returns:
            Dictionary mapping agent_id to energy extracted
        """
        results = {}

        for agent in agents:
            if agent.alive:
                energy = self.mine_energy(agent)
                results[agent.id] = energy

        return results

    def get_vacuum_status(self) -> Dict:
        """
        Get current vacuum status.

        Returns:
            Dictionary with vacuum metrics
        """
        return {
            "available_energy": self.total_vacuum_energy,
            "extracted_total": self.extracted_energy_total,
            "mining_rate": self.mining_rate,
            "extraction_efficiency": self.extraction_efficiency,
            "regeneration_rate": self.regeneration_rate,
            "depletion_warning": self.total_vacuum_energy < self.depletion_threshold,
            "critical_warning": self.total_vacuum_energy < self.critical_threshold,
            "utilization": self.extracted_energy_total
            / (self.extracted_energy_total + self.total_vacuum_energy),
        }

    def set_mining_rate(self, rate: float):
        """
        Set mining rate (human override).

        Args:
            rate: New mining rate (0.0 to 0.1)
        """
        self.mining_rate = np.clip(rate, 0.0, 0.1)
        logger.info(f"ZPE mining rate set to {self.mining_rate}")

    def set_efficiency(self, efficiency: float):
        """
        Set extraction efficiency (human override).

        Args:
            efficiency: New efficiency (0.0 to 1.0)
        """
        self.extraction_efficiency = np.clip(efficiency, 0.0, 1.0)
        logger.info(f"ZPE extraction efficiency set to {self.extraction_efficiency}")

    def emergency_refill(self, amount: float):
        """
        Emergency refill of vacuum energy (human override).

        Args:
            amount: Energy to add
        """
        self.total_vacuum_energy += amount
        logger.info(f"Emergency refill: added {amount} energy to vacuum")

    def get_energy_economy_stats(self, agents) -> Dict:
        """
        Compute energy economy statistics.

        Args:
            agents: List of agents to analyze

        Returns:
            Energy economy metrics
        """
        if not agents:
            return {}

        total_energy = sum(a.energy for a in agents if a.alive)
        avg_energy = total_energy / len([a for a in agents if a.alive])

        # Estimate consumption rates
        n_agents = len([a for a in agents if a.alive])

        # Rough estimates based on typical activity
        estimated_consumption = (
            n_agents * 0.01  # Coherence maintenance
            + n_agents * 0.05  # Movement
            + n_agents * 0.02  # Entanglement
        )

        # Mining income
        avg_entropy = 5.0  # Typical entropy value
        estimated_income = (
            n_agents * avg_entropy * self.mining_rate * self.extraction_efficiency
        )

        return {
            "total_agent_energy": total_energy,
            "avg_agent_energy": avg_energy,
            "estimated_consumption_per_epoch": estimated_consumption,
            "estimated_income_per_epoch": estimated_income,
            "equilibrium_delta": estimated_income - estimated_consumption,
            "is_sustainable": estimated_income >= estimated_consumption,
        }


# Extend QuantumAgent with ZPE method
def mine_zpe(self, amount: float):
    """Add energy from ZPE mining."""
    self.energy = min(self.energy + amount, self.max_energy)


QuantumAgent.mine_zpe = mine_zpe
