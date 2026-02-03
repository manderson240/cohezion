"""
GPU-accelerated physics simulation engine for COHEZION.

Provides CUDA-based physics calculations for real-time universal simulation.
Supports quantum field simulations, particle dynamics, and complex physical systems.
"""

import numpy as np
import cupy as cp
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PhysicsSimulationType(Enum):
    """Types of physics simulations supported."""

    QUANTUM_FIELD = "quantum_field"
    PARTICLE_DYNAMICS = "particle_dynamics"
    FLUID_DYNAMICS = "fluid_dynamics"
    GRAVITATIONAL = "gravitational"
    ELECTROMAGNETIC = "electromagnetic"


@dataclass
class PhysicsConfig:
    """Configuration for physics simulations."""

    simulation_type: PhysicsSimulationType
    grid_size: Tuple[int, int, int]
    timestep: float
    precision: str = "float32"
    gpu_device: int = 0
    max_particles: int = 1_000_000
    max_fields: int = 100


class GPUPhysicsEngine:
    """GPU-accelerated physics engine using CUDA."""

    def __init__(self, config: PhysicsConfig):
        self.config = config
        self._init_cuda()
        self._allocate_buffers()
        self._setup_simulation()

    def _init_cuda(self):
        """Initialize CUDA environment."""
        try:
            import cupy.cuda.runtime

            device_count = cupy.cuda.runtime.getDeviceCount()
            if device_count == 0:
                raise RuntimeError("No CUDA-capable devices found")

            if self.config.gpu_device >= device_count:
                raise RuntimeError(f"GPU device {self.config.gpu_device} not available")

            cp.cuda.Device(self.config.gpu_device).use()
            self.device_id = self.config.gpu_device
            self.total_memory = cp.cuda.runtime.getTotalMem(self.device_id)
            self.free_memory = cp.cuda.runtime.getFreeMem(self.device_id)

        except ImportError as e:
            raise RuntimeError("CUDA acceleration requires cupy library") from e

    def _allocate_buffers(self):
        """Allocate GPU memory buffers for simulation."""
        dtype = np.float32 if self.config.precision == "float32" else np.float64

        # Grid buffers
        self.grid_size = self.config.grid_size
        self.grid_volume = self.grid_size[0] * self.grid_size[1] * self.grid_size[2]

        self.particle_positions = cp.zeros((self.config.max_particles, 3), dtype=dtype)
        self.particle_velocities = cp.zeros((self.config.max_particles, 3), dtype=dtype)
        self.particle_masses = cp.zeros(self.config.max_particles, dtype=dtype)
        self.particle_charges = cp.zeros(self.config.max_particles, dtype=dtype)
        self.particle_types = cp.zeros(self.config.max_particles, dtype=np.int32)

        self.field_values = cp.zeros(
            (self.config.max_fields, *self.grid_size), dtype=dtype
        )
        self.field_sources = cp.zeros(
            (self.config.max_fields, *self.grid_size), dtype=dtype
        )

        # Simulation state
        self.active_particles = cp.zeros(1, dtype=np.int32)
        self.active_fields = cp.zeros(1, dtype=np.int32)

    def _setup_simulation(self):
        """Setup simulation based on configuration."""
        if self.config.simulation_type == PhysicsSimulationType.QUANTUM_FIELD:
            self._setup_quantum_field_simulation()
        elif self.config.simulation_type == PhysicsSimulationType.PARTICLE_DYNAMICS:
            self._setup_particle_dynamics_simulation()
        elif self.config.simulation_type == PhysicsSimulationType.FLUID_DYNAMICS:
            self._setup_fluid_dynamics_simulation()
        elif self.config.simulation_type == PhysicsSimulationType.GRAVITATIONAL:
            self._setup_gravitational_simulation()
        elif self.config.simulation_type == PhysicsSimulationType.ELECTROMAGNETIC:
            self._setup_electromagnetic_simulation()

    def _setup_quantum_field_simulation(self):
        """Setup quantum field simulation."""
        # Initialize quantum field parameters
        self.field_values[0] = cp.random.normal(
            size=self.grid_size, dtype=self.particle_positions.dtype
        )
        self.field_sources[0] = cp.zeros(
            self.grid_size, dtype=self.particle_positions.dtype
        )

    def _setup_particle_dynamics_simulation(self):
        """Setup particle dynamics simulation."""
        # Initialize particle system
        self.active_particles[0] = 1000  # Start with 1000 particles

        # Random initial positions and velocities
        self.particle_positions[:1000] = cp.random.uniform(
            low=-10, high=10, size=(1000, 3), dtype=self.particle_positions.dtype
        )
        self.particle_velocities[:1000] = cp.random.normal(
            scale=0.1, size=(1000, 3), dtype=self.particle_positions.dtype
        )
        self.particle_masses[:1000] = cp.random.uniform(
            low=0.1, high=1.0, size=1000, dtype=self.particle_positions.dtype
        )

    def _setup_fluid_dynamics_simulation(self):
        """Setup fluid dynamics simulation."""
        # Initialize fluid simulation parameters
        self.field_values[0] = cp.zeros(
            self.grid_size, dtype=self.particle_positions.dtype
        )
        self.field_sources[0] = cp.zeros(
            self.grid_size, dtype=self.particle_positions.dtype
        )

    def _setup_gravitational_simulation(self):
        """Setup gravitational simulation."""
        # Initialize gravitational system
        self.active_particles[0] = 500

        # Massive bodies at center
        self.particle_positions[:500] = cp.random.normal(
            scale=5, size=(500, 3), dtype=self.particle_positions.dtype
        )
        self.particle_masses[:500] = cp.random.uniform(
            low=1e3, high=1e6, size=500, dtype=self.particle_positions.dtype
        )

    def _setup_electromagnetic_simulation(self):
        """Setup electromagnetic simulation."""
        # Initialize electromagnetic system
        self.active_particles[0] = 2000

        # Charged particles
        self.particle_positions[:2000] = cp.random.uniform(
            low=-5, high=5, size=(2000, 3), dtype=self.particle_positions.dtype
        )
        self.particle_charges[:2000] = cp.random.choice(
            [-1.0, 1.0], size=2000, dtype=self.particle_positions.dtype
        )

    def add_particle(
        self,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float] = (0, 0, 0),
        mass: float = 1.0,
        charge: float = 0.0,
        particle_type: int = 0,
    ) -> int:
        """
        Add a particle to the simulation.

        Returns the particle index.
        """
        particle_idx = int(self.active_particles[0])
        if particle_idx >= self.config.max_particles:
            raise RuntimeError("Maximum particle limit reached")

        self.particle_positions[particle_idx] = position
        self.particle_velocities[particle_idx] = velocity
        self.particle_masses[particle_idx] = mass
        self.particle_charges[particle_idx] = charge
        self.particle_types[particle_idx] = particle_type

        self.active_particles[0] += 1
        return particle_idx

    def add_field_source(self, field_idx: int, source_values: np.ndarray) -> None:
        """Add field source values to the simulation."""
        if field_idx >= self.config.max_fields:
            raise IndexError("Field index out of range")

        self.field_sources[field_idx] = cp.asarray(
            source_values, dtype=self.field_sources.dtype
        )
        self.active_fields[0] = max(self.active_fields[0], field_idx + 1)

    def step(self) -> None:
        """Advance the simulation by one timestep."""
        if self.config.simulation_type == PhysicsSimulationType.QUANTUM_FIELD:
            self._step_quantum_field()
        elif self.config.simulation_type == PhysicsSimulationType.PARTICLE_DYNAMICS:
            self._step_particle_dynamics()
        elif self.config.simulation_type == PhysicsSimulationType.FLUID_DYNAMICS:
            self._step_fluid_dynamics()
        elif self.config.simulation_type == PhysicsSimulationType.GRAVITATIONAL:
            self._step_gravitational()
        elif self.config.simulation_type == PhysicsSimulationType.ELECTROMAGNETIC:
            self._step_electromagnetic()

    def _step_quantum_field(self) -> None:
        """Step quantum field simulation."""
        dt = self.config.timestep

        # Update field values based on sources and interactions
        for field_idx in range(int(self.active_fields[0])):
            # Simple diffusion model
            self.field_values[field_idx] += dt * self.field_sources[field_idx]

            # Apply boundary conditions
            self.field_values[field_idx] = cp.where(
                (self.field_values[field_idx] > 1.0)
                | (self.field_values[field_idx] < -1.0),
                cp.sign(self.field_values[field_idx]),
                self.field_values[field_idx],
            )

    def _step_particle_dynamics(self) -> None:
        """Step particle dynamics simulation."""
        dt = self.config.timestep
        num_particles = int(self.active_particles[0])

        # Calculate forces between particles
        forces = cp.zeros((num_particles, 3), dtype=self.particle_positions.dtype)

        for i in range(num_particles):
            for j in range(num_particles):
                if i != j:
                    # Calculate distance
                    diff = self.particle_positions[j] - self.particle_positions[i]
                    distance = cp.sqrt(cp.sum(diff**2))

                    if distance > 1e-6:
                        # Simple spring-like force
                        force_magnitude = 1.0 / distance**2
                        forces[i] += force_magnitude * diff / distance

        # Update velocities and positions
        self.particle_velocities[:num_particles] += dt * forces
        self.particle_positions[:num_particles] += (
            dt * self.particle_velocities[:num_particles]
        )

    def _step_fluid_dynamics(self) -> None:
        """Step fluid dynamics simulation."""
        dt = self.config.timestep

        # Simple advection-diffusion model
        for field_idx in range(int(self.active_fields[0])):
            # Advection
            self.field_values[field_idx] += dt * self.field_sources[field_idx]

            # Diffusion
            laplacian = (
                cp.roll(self.field_values[field_idx], shift=1, axis=0)
                + cp.roll(self.field_values[field_idx], shift=-1, axis=0)
                + cp.roll(self.field_values[field_idx], shift=1, axis=1)
                + cp.roll(self.field_values[field_idx], shift=-1, axis=1)
                + cp.roll(self.field_values[field_idx], shift=1, axis=2)
                + cp.roll(self.field_values[field_idx], shift=-1, axis=2)
                - 6 * self.field_values[field_idx]
            ) / 6.0

            self.field_values[field_idx] += dt * 0.1 * laplacian

    def _step_gravitational(self) -> None:
        """Step gravitational simulation."""
        dt = self.config.timestep
        num_particles = int(self.active_particles[0])

        # Calculate gravitational forces
        forces = cp.zeros((num_particles, 3), dtype=self.particle_positions.dtype)

        for i in range(num_particles):
            for j in range(num_particles):
                if i != j:
                    diff = self.particle_positions[j] - self.particle_positions[i]
                    distance = cp.sqrt(cp.sum(diff**2))

                    if distance > 1e-6:
                        force_magnitude = (
                            6.67430e-11
                            * self.particle_masses[i]
                            * self.particle_masses[j]
                            / distance**2
                        )
                        forces[i] += force_magnitude * diff / distance

        # Update velocities and positions
        self.particle_velocities[:num_particles] += dt * forces
        self.particle_positions[:num_particles] += (
            dt * self.particle_velocities[:num_particles]
        )

    def _step_electromagnetic(self) -> None:
        """Step electromagnetic simulation."""
        dt = self.config.timestep
        num_particles = int(self.active_particles[0])

        # Calculate electromagnetic forces
        forces = cp.zeros((num_particles, 3), dtype=self.particle_positions.dtype)

        for i in range(num_particles):
            for j in range(num_particles):
                if i != j:
                    diff = self.particle_positions[j] - self.particle_positions[i]
                    distance = cp.sqrt(cp.sum(diff**2))

                    if distance > 1e-6:
                        # Coulomb force
                        k = 8.9875517923e9
                        force_magnitude = (
                            k
                            * self.particle_charges[i]
                            * self.particle_charges[j]
                            / distance**2
                        )
                        forces[i] += force_magnitude * diff / distance

        # Update velocities and positions
        self.particle_velocities[:num_particles] += dt * forces
        self.particle_positions[:num_particles] += (
            dt * self.particle_velocities[:num_particles]
        )

    def get_particle_data(self) -> Dict[str, np.ndarray]:
        """Get current particle data."""
        return {
            "positions": cp.asnumpy(
                self.particle_positions[: int(self.active_particles[0])]
            ),
            "velocities": cp.asnumpy(
                self.particle_velocities[: int(self.active_particles[0])]
            ),
            "masses": cp.asnumpy(self.particle_masses[: int(self.active_particles[0])]),
            "charges": cp.asnumpy(
                self.particle_charges[: int(self.active_particles[0])]
            ),
            "types": cp.asnumpy(self.particle_types[: int(self.active_particles[0])]),
        }

    def get_field_data(self) -> Dict[str, np.ndarray]:
        """Get current field data."""
        return {
            f"field_{i}": cp.asnumpy(self.field_values[i])
            for i in range(int(self.active_fields[0]))
        }

    def get_memory_usage(self) -> Dict[str, int]:
        """Get GPU memory usage statistics."""
        return {
            "total_memory_mb": int(self.total_memory / (1024 * 1024)),
            "free_memory_mb": int(self.free_memory / (1024 * 1024)),
            "used_memory_mb": int(
                (self.total_memory - self.free_memory) / (1024 * 1024)
            ),
            "particle_memory_mb": int(self.particle_positions.nbytes / (1024 * 1024)),
            "field_memory_mb": int(self.field_values.nbytes / (1024 * 1024)),
        }

    def get_performance_metrics(self) -> Dict[str, float]:
        """Get simulation performance metrics."""
        num_particles = int(self.active_particles[0])
        num_fields = int(self.active_fields[0])

        return {
            "particles": num_particles,
            "fields": num_fields,
            "timestep": self.config.timestep,
            "particles_per_second": num_particles / self.config.timestep,
            "field_updates_per_second": num_fields / self.config.timestep,
        }


class PhysicsSimulationManager:
    """Manager for multiple physics simulations."""

    def __init__(self):
        self.simulations: Dict[str, GPUPhysicsEngine] = {}
        self.default_config = PhysicsConfig(
            simulation_type=PhysicsSimulationType.PARTICLE_DYNAMICS,
            grid_size=(64, 64, 64),
            timestep=0.01,
            precision="float32",
            gpu_device=0,
        )

    def create_simulation(
        self, name: str, config: Optional[PhysicsConfig] = None
    ) -> GPUPhysicsEngine:
        """Create a new physics simulation."""
        if name in self.simulations:
            raise ValueError(f"Simulation '{name}' already exists")

        if config is None:
            config = self.default_config

        engine = GPUPhysicsEngine(config)
        self.simulations[name] = engine
        return engine

    def get_simulation(self, name: str) -> GPUPhysicsEngine:
        """Get an existing physics simulation."""
        if name not in self.simulations:
            raise ValueError(f"Simulation '{name}' not found")

        return self.simulations[name]

    def remove_simulation(self, name: str) -> None:
        """Remove a physics simulation."""
        if name in self.simulations:
            del self.simulations[name]

    def list_simulations(self) -> List[str]:
        """List all active simulations."""
        return list(self.simulations.keys())


# Example usage
if __name__ == "__main__":
    # Create simulation manager
    manager = PhysicsSimulationManager()

    # Create a particle dynamics simulation
    particle_sim = manager.create_simulation(
        "particle_dynamics",
        PhysicsConfig(
            simulation_type=PhysicsSimulationType.PARTICLE_DYNAMICS,
            grid_size=(128, 128, 128),
            timestep=0.001,
            precision="float32",
            gpu_device=0,
            max_particles=100000,
        ),
    )

    # Add particles
    for _ in range(1000):
        particle_sim.add_particle(
            position=(
                np.random.uniform(-10, 10),
                np.random.uniform(-10, 10),
                np.random.uniform(-10, 10),
            ),
            velocity=(
                np.random.normal(scale=0.1),
                np.random.normal(scale=0.1),
                np.random.normal(scale=0.1),
            ),
            mass=np.random.uniform(0.1, 1.0),
            charge=np.random.choice([-1.0, 1.0]),
        )

    # Run simulation
    for step in range(1000):
        particle_sim.step()

        if step % 100 == 0:
            data = particle_sim.get_particle_data()
            print(f"Step {step}: {len(data['positions'])} particles")
            print(f"Memory usage: {particle_sim.get_memory_usage()}")
            print(f"Performance: {particle_sim.get_performance_metrics()}")
