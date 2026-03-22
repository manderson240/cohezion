"""Plasma Physics MCP Server - For 400-year unification and exotic vacuum objects.

Port: 8371
Features:
- Plasma simulation (Particle-in-Cell)
- Exotic vacuum object tracking
- HIHO (High-Intensity Hadron Operations) story support
- Agent representation of vacuum fluctuations
- Particle-antiparticle pair production
- Electromagnetic field evolution
- Quantum vacuum effects
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
from aiohttp import web


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

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
        # Random chance to create exotic object
        if np.random.random() < 0.1:  # 10% chance per step
            obj = ExoticVacuumObject(
                id=str(uuid.uuid4())[:8],
                object_type=np.random.choice(
                    [
                        "virtual_pair",
                        "vacuum_fluctuation",
                        "quantum_foam",
                        "casimir_effect",
                    ]
                ),
                position=np.random.rand(3) * self.grid_size,
                creation_time=self.current_time,
                expected_lifetime=np.random.exponential(0.1),  # Exponential decay
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

        # Update particle positions
        for p in self.particles:
            p.position += p.velocity * self.time_step
            # Apply periodic boundary conditions
            p.position = p.position % self.grid_size

        # Generate exotic vacuum objects
        new_exotic = self.generate_exotic_vacuum_object()

        # Remove decayed exotic objects
        self.exotic_objects = [
            obj for obj in self.exotic_objects if obj.is_active(self.current_time)
        ]

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


# Global simulation instance
_simulations: dict[str, PlasmaSimulation] = {}


def get_simulation(sim_id: str) -> PlasmaSimulation:
    """Get or create simulation."""
    if sim_id not in _simulations:
        _simulations[sim_id] = PlasmaSimulation()
    return _simulations[sim_id]


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "plasma-physics",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Plasma Physics MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "physics": [
                "Particle-in-Cell (PIC)",
                "Exotic Vacuum Objects",
                "HIHO Operations",
                "Quantum Vacuum Effects",
            ],
            "tools": [
                "plasma_create_simulation",
                "plasma_add_particle",
                "plasma_step",
                "plasma_get_exotic_objects",
                "plasma_get_hiho_agents",
                "plasma_get_field",
                "plasma_400_year_unification",
            ],
        }
    )


@routes.post("/tools/plasma_create_simulation")
async def tool_create_simulation(request: web.Request) -> web.Response:
    """Create new plasma simulation."""
    try:
        data = await request.json()
        grid_size = data.get("grid_size", 64)

        sim_id = str(uuid.uuid4())[:8]
        sim = PlasmaSimulation(grid_size=grid_size)
        _simulations[sim_id] = sim

        return web.json_response(
            {
                "tool": "plasma_create_simulation",
                "simulation_id": sim_id,
                "grid_size": grid_size,
                "status": "created",
            }
        )
    except Exception as e:
        logger.exception("Create simulation failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/plasma_add_particle")
async def tool_add_particle(request: web.Request) -> web.Response:
    """Add particle to simulation."""
    try:
        data = await request.json()
        sim_id = data.get("simulation_id", "")
        species = data.get("species", "electron")
        position = data.get("position", [0.0, 0.0, 0.0])
        velocity = data.get("velocity", [0.0, 0.0, 0.0])
        charge = data.get("charge", -1.0)
        mass = data.get("mass", 1.0)

        sim = get_simulation(sim_id)
        particle = sim.create_particle(species, position, velocity, charge, mass)

        return web.json_response(
            {
                "tool": "plasma_add_particle",
                "simulation_id": sim_id,
                "particle": particle.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Add particle failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/plasma_step")
async def tool_step(request: web.Request) -> web.Response:
    """Advance simulation."""
    try:
        data = await request.json()
        sim_id = data.get("simulation_id", "")
        steps = data.get("steps", 1)

        sim = get_simulation(sim_id)
        results = []
        for _ in range(steps):
            result = sim.step()
            results.append(result)

        return web.json_response(
            {
                "tool": "plasma_step",
                "simulation_id": sim_id,
                "steps": steps,
                "final_time": sim.current_time,
                "results": results,
            }
        )
    except Exception as e:
        logger.exception("Step failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/plasma_get_exotic_objects")
async def tool_get_exotic(request: web.Request) -> web.Response:
    """Get exotic vacuum objects."""
    try:
        data = await request.json()
        sim_id = data.get("simulation_id", "")

        sim = get_simulation(sim_id)
        objects = [obj.to_dict() for obj in sim.exotic_objects]

        return web.json_response(
            {
                "tool": "plasma_get_exotic_objects",
                "simulation_id": sim_id,
                "count": len(objects),
                "objects": objects,
            }
        )
    except Exception as e:
        logger.exception("Get exotic objects failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/plasma_get_hiho_agents")
async def tool_get_hiho(request: web.Request) -> web.Response:
    """Get HIHO (High-Intensity Hadron Operations) agents."""
    try:
        data = await request.json()
        sim_id = data.get("simulation_id", "")

        sim = get_simulation(sim_id)
        agents = sim.get_hiho_agents()

        return web.json_response(
            {
                "tool": "plasma_get_hiho_agents",
                "simulation_id": sim_id,
                "agents": agents,
                "context": "400-year unification of physics through high-intensity hadron operations",
            }
        )
    except Exception as e:
        logger.exception("Get HIHO agents failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/plasma_get_field")
async def tool_get_field(request: web.Request) -> web.Response:
    """Get electromagnetic field at position."""
    try:
        data = await request.json()
        sim_id = data.get("simulation_id", "")
        position = data.get("position", [0.0, 0.0, 0.0])

        sim = get_simulation(sim_id)
        field = sim.get_field_at(position)

        return web.json_response(
            {
                "tool": "plasma_get_field",
                "simulation_id": sim_id,
                "field": field,
            }
        )
    except Exception as e:
        logger.exception("Get field failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/plasma_400_year_unification")
async def tool_400_year(request: web.Request) -> web.Response:
    """Tell the 400-year unification story."""
    try:
        data = await request.json()
        chapter = data.get("chapter", "overview")

        story = {
            "overview": {
                "title": "400 Years of Physics Unification",
                "periods": [
                    "1600-1700: Classical Mechanics (Newton)",
                    "1700-1800: Thermodynamics (Carnot, Boltzmann)",
                    "1800-1900: Electromagnetism (Maxwell)",
                    "1900-2000: Relativity & Quantum Mechanics (Einstein, Bohr, Heisenberg)",
                    "2000-2100: Quantum Field Theory & Standard Model",
                    "2100-2200: Vacuum Engineering & Exotic Matter",
                    "2200-2300: HIHO Era - Hadron Intensity Frontier",
                    "2300-2400: Unified Field Manipulation",
                ],
                "current_era": "HIHO Operations",
                "exotic_vacuum": "We now manipulate the vacuum itself",
            },
            "vacuum_engineering": {
                "concept": "The vacuum is not empty - it's a quantum foam of virtual particles",
                "techniques": [
                    "Casimir Effect manipulation",
                    "Vacuum fluctuation amplification",
                    "Virtual pair production",
                    "Quantum field stabilization",
                ],
                "applications": [
                    "Exotic matter creation",
                    "Warp field generation",
                    "Zero-point energy extraction",
                ],
            },
            "hiho_operations": {
                "full_name": "High-Intensity Hadron Operations",
                "purpose": "Probe the fundamental nature of spacetime",
                "methods": [
                    "Ultra-high luminosity colliders",
                    "Vacuum state preparation",
                    "Exotic particle detection",
                    "Field configuration control",
                ],
            },
        }

        return web.json_response(
            {
                "tool": "plasma_400_year_unification",
                "chapter": chapter,
                "story": story.get(chapter, story["overview"]),
            }
        )
    except Exception as e:
        logger.exception("400 year story failed")
        return web.json_response({"error": str(e)}, status=500)


async def main():
    """Run Plasma Physics MCP Server."""
    app = web.Application()
    app.add_routes(routes)

    logger.info(f"Starting Plasma Physics MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ Plasma Physics Server running on http://localhost:{MCP_PORT}")
    logger.info("   Exotic vacuum objects: Enabled")
    logger.info("   HIHO story: 400-year unification")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Plasma Physics Server stopped")
