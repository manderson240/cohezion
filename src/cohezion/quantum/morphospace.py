"""
Bioelectric Morphospace
Michael Levin-inspired navigation using voltage gradients.
"""

import numpy as np
from typing import Dict, Tuple
from dataclasses import dataclass
import logging

from .quantum_state import QuantumAgent

logger = logging.getLogger(__name__)


@dataclass
class StabilityWell:
    """Stability well in 12D morphospace."""

    name: str
    position: np.ndarray
    description: str
    strength: float = 1.0  # Human-tweakable


class BioelectricMorphospace:
    """
    Bioelectric navigation system for quantum agents.

    Agents navigate toward stability wells using voltage gradients.
    Inspired by Michael Levin's work on bioelectric morphogenesis.
    """

    def __init__(self):
        """Initialize morphospace with stability wells."""
        self.wells: Dict[str, StabilityWell] = {}
        self._initialize_default_wells()

        logger.info(f"Bioelectric morphospace initialized with {len(self.wells)} wells")

    def _initialize_default_wells(self):
        """Create default stability wells."""
        # HIHO_Origin - Balanced stability
        self.wells["HIHO_Origin"] = StabilityWell(
            name="HIHO_Origin",
            position=np.array([0.5] * 12),
            description="Balanced stability (Half-In-Half-Out)",
            strength=1.0,
        )

        # Pure_Awareness - Consciousness focus
        self.wells["Pure_Awareness"] = StabilityWell(
            name="Pure_Awareness",
            position=np.array([1.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
            description="Pure consciousness focus",
            strength=0.5,
        )

        # Creative_Mode - High novelty
        self.wells["Creative_Mode"] = StabilityWell(
            name="Creative_Mode",
            position=np.array(
                [0.3, 0.8, 0.8, 0.2, 0.9, 0.9, 0.8, 0.8, 0.1, 0.7, 0.6, 0.4]
            ),
            description="High novelty generation",
            strength=0.8,
        )

        # Analytical_Mode - Precision
        self.wells["Analytical_Mode"] = StabilityWell(
            name="Analytical_Mode",
            position=np.array(
                [0.8, 0.2, 0.2, 0.9, 0.1, 0.1, 0.2, 0.2, 0.9, 0.1, 0.9, 0.9]
            ),
            description="Precision and logic",
            strength=0.8,
        )

    def get_voltage(
        self, position: np.ndarray, well_name: str = "HIHO_Origin"
    ) -> float:
        """
        Compute bioelectric voltage at position.

        Voltage represents distance from stability:
        - -1.0 = far from stability (high force needed)
        - 0.0 = perfect stability (equilibrium)
        - 1.0 = too close/unstable

        Args:
            position: 12D position vector
            well_name: Name of stability well

        Returns:
            Voltage value
        """
        if well_name not in self.wells:
            well_name = "HIHO_Origin"

        well = self.wells[well_name]
        distance = np.linalg.norm(position - well.position)

        # Hyperbolic tangent for smooth [-1, 1] mapping
        voltage = np.tanh(distance * 2 - 1)

        # Apply well strength (human tweakable)
        voltage *= well.strength

        return voltage

    def compute_gradient(
        self, position: np.ndarray, agent_age: int
    ) -> Tuple[np.ndarray, str]:
        """
        Compute morphogenetic gradient toward preferred well.

        Age determines preferred stability well.

        Args:
            position: Current 12D position
            agent_age: Age of agent in epochs

        Returns:
            (gradient_vector, well_name)
        """
        # Age-dependent well preference
        if agent_age < 10:
            preferred = "HIHO_Origin"  # Juvenile: learn basics
        elif agent_age < 30:
            preferred = "Creative_Mode"  # Young: explore
        elif agent_age < 50:
            preferred = "Analytical_Mode"  # Mature: exploit
        else:
            preferred = "Pure_Awareness"  # Elderly: wisdom

        well = self.wells[preferred]

        # Compute gradient direction
        gradient = well.position - position

        # Normalize
        norm = np.linalg.norm(gradient)
        if norm > 0:
            gradient = gradient / norm

        return gradient, preferred

    def apply_bioelectric_force(self, agent: QuantumAgent) -> Tuple[str, float]:
        """
        Apply bioelectric force to move agent toward stability.

        Args:
            agent: QuantumAgent to move

        Returns:
            (target_well, voltage)
        """
        # Compute gradient toward preferred well
        gradient, target_well = self.compute_gradient(agent.position_12d, agent.age)

        # Get voltage at current position
        voltage = self.get_voltage(agent.position_12d, target_well)

        # Determine movement magnitude
        if voltage < 0:
            # Far from stability - strong force
            move_magnitude = 0.1 * abs(voltage)
        else:
            # Close to stability - weak force
            move_magnitude = 0.01

        # Apply movement
        agent.position_12d += gradient * move_magnitude

        # Renormalize to unit sphere
        norm = np.linalg.norm(agent.position_12d)
        if norm > 0:
            agent.position_12d = agent.position_12d / norm

        # Energy cost
        energy_cost = 0.05 * move_magnitude
        agent.energy -= energy_cost

        # Update agent's target well
        agent.target_well = target_well
        agent.current_voltage = voltage

        return target_well, voltage

    def set_well_strength(self, well_name: str, strength: float):
        """
        Set strength of a stability well (human override).

        Args:
            well_name: Name of well to modify
            strength: New strength value (0.0 to 2.0)
        """
        if well_name in self.wells:
            self.wells[well_name].strength = np.clip(strength, 0.0, 2.0)
            logger.info(f"Set {well_name} strength to {strength}")
        else:
            logger.warning(f"Well {well_name} not found")

    def add_custom_well(
        self, name: str, position: np.ndarray, description: str, strength: float = 1.0
    ):
        """
        Add custom stability well (human override).

        Args:
            name: Well name
            position: 12D position
            description: Description
            strength: Initial strength
        """
        self.wells[name] = StabilityWell(
            name=name, position=position, description=description, strength=strength
        )
        logger.info(f"Added custom well: {name}")

    def get_well_positions(self) -> Dict[str, np.ndarray]:
        """Get positions of all wells for visualization."""
        return {name: well.position for name, well in self.wells.items()}

    def get_well_strengths(self) -> Dict[str, float]:
        """Get strengths of all wells."""
        return {name: well.strength for name, well in self.wells.items()}
