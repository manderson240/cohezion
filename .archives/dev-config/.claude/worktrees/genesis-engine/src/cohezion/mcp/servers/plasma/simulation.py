"""Plasma Physics MCP Server - PlasmaSimulation class."""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np

from .models import ExoticVacuumObject, Particle


class PlasmaSimulation:
    """Particle-in-Cell plasma simulation."""

    def __init__(self, grid_size: int = 64):
        self.grid_size = grid_size
        self.particles: list[Particle] = []
        self.exotic_objects: list[ExoticVacuumObject] = []
        self.electric_field = np.zeros((grid_size, grid_size, grid_size, 3))
        self.magnetic_field = np.zeros((grid_size, grid_size, grid_size, 3))
        self.current_time: float = 0.0
        self.time_step: float = 0.01

    def create_particle(
        self,
        species: str,
        position: list[float],
        velocity: list[float],
        charge: float,
        mass: float,
    ) -> Particle:
        """Create a particle in the simulation."""
        particle = Particle(
            id=str(uuid.uuid4())[:8],
            species=species,
            position=np.array(position),
            velocity=np.array(velocity),
            charge=charge,
            mass=mass,
            birth_time=self.current_time,
        )
        self.particles.append(particle)
        return particle

    def generate_exotic_vacuum_object(self) -> ExoticVacuumObject | None:
        """Generate an exotic vacuum object (quantum fluctuation)."""
        if np.random.random() < 0.1:  # 10% chance per step
            obj = ExoticVacuumObject(
                id=str(uuid.uuid4())[:8],
                object_type=np.random.choice(["virtual_pair", "vacuum_fluctuation", "quantum_foam", "casimir_effect"]),
                position=np.random.rand(3) * self.grid_size,
                creation_time=self.current_time,
                expected_lifetime=np.random.exponential(0.1),
                energy=np.random.exponential(1.0),
                agent_representation=self._generate_agent_description(),
            )
            self.exotic_objects.append(obj)
            return obj
        return None

    def _generate_agent_description(self) -> str:
        """Generate an agent description for an exotic vacuum object."""
        descriptions = [
            "A fleeting presence in the quantum foam, manifesting as energy fluctuations.",
            "Virtual particles dancing at the edge of existence, momentarily real.",
            "The vacuum itself stirs, creating ephemeral agents of pure potential.",
            "Quantum uncertainty made manifest - here, then gone, yet leaving traces.",
            "An echo of the Big Bang, still reverberating through spacetime.",
        ]
        return np.random.choice(descriptions)

    def step(self) -> dict[str, Any]:
        """Advance simulation by one time step."""
        self.current_time += self.time_step

        for p in self.particles:
            p.position += p.velocity * self.time_step
            p.position = p.position % self.grid_size

        new_exotic = self.generate_exotic_vacuum_object()

        self.exotic_objects = [obj for obj in self.exotic_objects if obj.is_active(self.current_time)]

        return {
            "time": self.current_time,
            "particle_count": len(self.particles),
            "exotic_objects_count": len(self.exotic_objects),
            "new_exotic_object": new_exotic.to_dict() if new_exotic else None,
        }

    def get_hiho_agents(self) -> list[dict]:
        """Get agents representing HIHO (High-Intensity Hadron Operations)."""
        return [
            {
                "name": "Accelerator Operator",
                "role": "Controls beam intensity and collision parameters",
                "expertise": ["beam_dynamics", "vacuum_systems", "safety_protocols"],
            },
            {
                "name": "Vacuum Physicist",
                "role": "Studies exotic vacuum phenomena",
                "expertise": ["quantum_field_theory", "vacuum_fluctuations", "casimir_effects"],
            },
            {
                "name": "Plasma Diagnostics",
                "role": "Monitors plasma conditions and instabilities",
                "expertise": ["langmuir_probes", "spectroscopy", "tomography"],
            },
        ]

    def get_field_at(self, position: list[float]) -> dict[str, Any]:
        """Get electromagnetic field at a specific position."""
        idx = [int(p) % self.grid_size for p in position]
        return {
            "position": position,
            "electric_field": self.electric_field[idx[0], idx[1], idx[2]].tolist(),
            "magnetic_field": self.magnetic_field[idx[0], idx[1], idx[2]].tolist(),
        }


# Global simulation instances
_simulations: dict[str, PlasmaSimulation] = {}


def get_simulation(sim_id: str) -> PlasmaSimulation:
    """Get or create simulation."""
    if sim_id not in _simulations:
        _simulations[sim_id] = PlasmaSimulation()
    return _simulations[sim_id]
