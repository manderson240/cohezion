"""Plasma Physics MCP Server - data models."""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np


MCP_PORT = int(os.getenv("MCP_PORT", "8371"))


@dataclass
class Particle:
    """A particle in the plasma simulation."""

    id: str
    species: str  # electron, ion, positron, etc.
    position: np.ndarray  # 3D position
    velocity: np.ndarray  # 3D velocity
    charge: float
    mass: float
    birth_time: float
    lifetime: float | None = None  # For exotic objects
    is_exotic: bool = False  # Exotic vacuum object flag

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "species": self.species,
            "position": self.position.tolist(),
            "velocity": self.velocity.tolist(),
            "charge": self.charge,
            "mass": self.mass,
            "birth_time": self.birth_time,
            "lifetime": self.lifetime,
            "is_exotic": self.is_exotic,
        }


@dataclass
class ExoticVacuumObject:
    """Exotic vacuum object that pops in and out of existence."""

    id: str
    object_type: str  # virtual_pair, vacuum_fluctuation, quantum_foam
    position: np.ndarray
    creation_time: float
    expected_lifetime: float
    energy: float
    agent_representation: str  # How this object appears as an agent

    def is_active(self, current_time: float) -> bool:
        """Check if object still exists."""
        return current_time - self.creation_time < self.expected_lifetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.object_type,
            "position": self.position.tolist(),
            "creation_time": self.creation_time,
            "expected_lifetime": self.expected_lifetime,
            "energy": self.energy,
            "agent_representation": self.agent_representation,
            "is_active": True,
        }
