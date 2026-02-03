"""
GPU acceleration manager for COHEZION physics simulations.

Integrates CUDA-based physics engines with the existing agentic infrastructure.
Provides real-time simulation capabilities and performance optimization.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import cupy as cp

from .physics_simulation import (
    GPUPhysicsEngine,
    PhysicsSimulationManager,
    PhysicsSimulationType,
    PhysicsConfig,
)
from .agents.base import Agent
from .core.cache_manager import CacheManager
from .core.connection_pool import ConnectionPool


class SimulationState(Enum):
    """States of physics simulations."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class SimulationMetrics:
    """Metrics for physics simulations."""

    fps: float
    latency_ms: float
    particles: int
    memory_usage_mb: float
    gpu_utilization: float
    temperature_c: float


class GPUAccelerationManager:
    """Manages GPU-accelerated physics simulations across the system."""

    def __init__(self):
        self.simulation_manager = PhysicsSimulationManager()
        self.active_simulations: Dict[str, GPUPhysicsEngine] = {}
        self.agent_simulations: Dict[str, List[str]] = {}
        self.simulation_states: Dict[str, SimulationState] = {}
        self.metrics_cache: Dict[str, SimulationMetrics] = {}
        self.cache_manager = CacheManager()
        self.connection_pool = ConnectionPool()
        self._init_gpu_resources()

    def _init_gpu_resources(self):
        """Initialize GPU resources and check availability."""
        try:
            import cupy.cuda.runtime

            self.device_count = cupy.cuda.runtime.getDeviceCount()
            self.devices = []

            for device_id in range(self.device_count):
                device = cp.cuda.Device(device_id)
                device.use()
                self.devices.append(
                    {
                        "id": device_id,
                        "name": device.name(),
                        "total_memory": device.mem_info[0] + device.mem_info[1],
                        "free_memory": device.mem_info[0],
                        "temperature": self._get_gpu_temperature(device_id),
                    }
                )

            if self.device_count == 0:
                raise RuntimeError("No CUDA-capable devices found")

        except ImportError as e:
            raise RuntimeError("CUDA acceleration requires cupy library") from e

    def _get_gpu_temperature(self, device_id: int) -> float:
        """Get GPU temperature (platform-specific)."""
        try:
            import subprocess

            # Try nvidia-smi for NVIDIA GPUs
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                temps = [float(line) for line in result.stdout.splitlines()]
                return temps[device_id] if device_id < len(temps) else 0.0

        except Exception:
            return 0.0  # Temperature monitoring not available

    def create_simulation(
        self,
        agent: Agent,
        simulation_type: PhysicsSimulationType = PhysicsSimulationType.PARTICLE_DYNAMICS,
        name: Optional[str] = None,
    ) -> str:
        """
        Create a physics simulation for an agent.

        Returns the simulation name.
        """
        if name is None:
            name = f"{agent.name}_sim_{len(self.active_simulations)}"

        if name in self.active_simulations:
            raise ValueError(f"Simulation '{name}' already exists")

        # Get agent-specific configuration
        config = self._get_agent_simulation_config(agent, simulation_type)

        # Create simulation
        simulation = self.simulation_manager.create_simulation(name, config)
        self.active_simulations[name] = simulation
        self.simulation_states[name] = SimulationState.IDLE

        # Track agent-simulation relationship
        if agent.id not in self.agent_simulations:
            self.agent_simulations[agent.id] = []
        self.agent_simulations[agent.id].append(name)

        return name

    def _get_agent_simulation_config(
        self, agent: Agent, simulation_type: PhysicsSimulationType
    ) -> PhysicsConfig:
        """Generate simulation configuration based on agent capabilities."""
        # Get agent's resource requirements and capabilities
        resource_profile = agent.get_resource_profile()
        capability_profile = agent.get_capability_profile()

        # Calculate appropriate simulation parameters
        max_particles = min(
            100000,  # Default max
            int(resource_profile["memory_mb"] / 10),  # 10MB per particle
            int(resource_profile["cpu_cores"] * 1000),  # 1000 particles per CPU core
        )

        grid_size = self._calculate_grid_size(max_particles)
        timestep = self._calculate_timestep(agent)

        return PhysicsConfig(
            simulation_type=simulation_type,
            grid_size=grid_size,
            timestep=timestep,
            precision="float32",
            gpu_device=self._select_gpu_device(agent),
            max_particles=max_particles,
            max_fields=10,
        )

    def _calculate_grid_size(self, max_particles: int) -> Tuple[int, int, int]:
        """Calculate optimal grid size based on particle count."""
        # Start with cubic grid
        base_size = int(max_particles ** (1 / 3))

        # Adjust for performance (power of 2 is optimal for GPU)
        size = 2 ** int(np.log2(base_size) + 0.5)

        # Ensure minimum size
        size = max(size, 32)

        # Limit maximum size for performance
        size = min(size, 256)

        return (size, size, size)

    def _calculate_timestep(self, agent: Agent) -> float:
        """Calculate optimal timestep based on agent capabilities."""
        # Agents with higher computational resources can handle smaller timesteps
        cpu_speed = agent.get_resource_profile().get("cpu_speed_ghz", 2.0)

        # Base timestep of 1ms, adjusted by CPU speed
        base_timestep = 0.001
        adjusted_timestep = base_timestep / (cpu_speed / 2.0)

        # Clamp to reasonable range
        return max(0.0001, min(0.01, adjusted_timestep))

    def _select_gpu_device(self, agent: Agent) -> int:
        """Select optimal GPU device for the agent."""
        # For now, use the first available device
        # In future: implement device affinity based on agent requirements
        return 0

    def start_simulation(self, name: str) -> None:
        """Start a physics simulation."""
        if name not in self.active_simulations:
            raise ValueError(f"Simulation '{name}' not found")

        self.simulation_states[name] = SimulationState.RUNNING

        # Start simulation in background
        asyncio.create_task(self._run_simulation(name))

    async def _run_simulation(self, name: str) -> None:
        """Run simulation in background."""
        simulation = self.active_simulations[name]

        try:
            while self.simulation_states[name] == SimulationState.RUNNING:
                # Step simulation
                simulation.step()

                # Update metrics
                self._update_metrics(name)

                # Cache simulation state
                self._cache_simulation_state(name)

                # Wait for next timestep
                await asyncio.sleep(simulation.config.timestep)

        except Exception as e:
            self.simulation_states[name] = SimulationState.ERROR
            print(f"Simulation {name} encountered error: {e}")

    def _update_metrics(self, name: str) -> None:
        """Update simulation metrics."""
        simulation = self.active_simulations[name]

        # Calculate FPS
        fps = 1.0 / simulation.config.timestep

        # Get memory usage
        memory_usage = simulation.get_memory_usage()
        memory_mb = memory_usage["used_memory_mb"]

        # Estimate GPU utilization (simplified)
        gpu_utilization = min(100.0, (memory_mb / 8192) * 100)  # Assume 8GB GPU

        # Get temperature
        temperature = self._get_gpu_temperature(simulation.device_id)

        self.metrics_cache[name] = SimulationMetrics(
            fps=fps,
            latency_ms=simulation.config.timestep * 1000,
            particles=simulation.get_particle_data()["positions"].shape[0],
            memory_usage_mb=memory_mb,
            gpu_utilization=gpu_utilization,
            temperature_c=temperature,
        )

    def _cache_simulation_state(self, name: str) -> None:
        """Cache simulation state for quick access."""
        simulation = self.active_simulations[name]

        # Cache particle data
        particle_data = simulation.get_particle_data()
        self.cache_manager.set(f"{name}_particles", particle_data, ttl=60)

        # Cache field data
        field_data = simulation.get_field_data()
        self.cache_manager.set(f"{name}_fields", field_data, ttl=60)

        # Cache metrics
        metrics = self.metrics_cache.get(name, SimulationMetrics(0, 0, 0, 0, 0, 0))
        self.cache_manager.set(f"{name}_metrics", metrics.__dict__, ttl=30)

    def get_simulation_state(self, name: str) -> Dict[str, any]:
        """Get complete simulation state."""
        if name not in self.active_simulations:
            raise ValueError(f"Simulation '{name}' not found")

        simulation = self.active_simulations[name]

        return {
            "name": name,
            "state": self.simulation_states[name].value,
            "type": simulation.config.simulation_type.value,
            "particles": simulation.get_particle_data(),
            "fields": simulation.get_field_data(),
            "metrics": self.metrics_cache.get(
                name, SimulationMetrics(0, 0, 0, 0, 0, 0)
            ).__dict__,
            "memory": simulation.get_memory_usage(),
            "performance": simulation.get_performance_metrics(),
        }

    def get_agent_simulations(self, agent_id: str) -> List[Dict[str, any]]:
        """Get all simulations for an agent."""
        if agent_id not in self.agent_simulations:
            return []

        return [
            self.get_simulation_state(name) for name in self.agent_simulations[agent_id]
        ]

    def pause_simulation(self, name: str) -> None:
        """Pause a simulation."""
        if name in self.active_simulations:
            self.simulation_states[name] = SimulationState.PAUSED

    def resume_simulation(self, name: str) -> None:
        """Resume a paused simulation."""
        if name in self.active_simulations:
            if self.simulation_states[name] == SimulationState.PAUSED:
                self.simulation_states[name] = SimulationState.RUNNING
                asyncio.create_task(self._run_simulation(name))

    def stop_simulation(self, name: str) -> None:
        """Stop a simulation."""
        if name in self.active_simulations:
            self.simulation_states[name] = SimulationState.IDLE
            # Remove from active simulations
            del self.active_simulations[name]

            # Remove from agent mappings
            for agent_id, simulations in self.agent_simulations.items():
                if name in simulations:
                    simulations.remove(name)
                    break

    def get_system_metrics(self) -> Dict[str, any]:
        """Get system-wide GPU and simulation metrics."""
        total_particles = 0
        total_fields = 0
        total_memory_mb = 0
        max_temperature = 0

        for name, simulation in self.active_simulations.items():
            data = simulation.get_particle_data()
            total_particles += len(data["positions"])

            fields = simulation.get_field_data()
            total_fields += len(fields)

            memory = simulation.get_memory_usage()
            total_memory_mb += memory["used_memory_mb"]

            # Track maximum temperature
            temperature = self._get_gpu_temperature(simulation.device_id)
            max_temperature = max(max_temperature, temperature)

        return {
            "active_simulations": len(self.active_simulations),
            "total_particles": total_particles,
            "total_fields": total_fields,
            "total_memory_mb": total_memory_mb,
            "max_temperature_c": max_temperature,
            "gpu_devices": self.devices,
            "simulation_states": {
                name: state.value for name, state in self.simulation_states.items()
            },
        }

    def integrate_with_agent(self, agent: Agent) -> None:
        """Integrate GPU acceleration with an agent's capabilities."""
        # Create simulation for the agent
        simulation_name = self.create_simulation(agent)

        # Start simulation
        self.start_simulation(simulation_name)

        # Update agent with simulation capabilities
        agent.add_capability(
            "physics_simulation",
            {
                "simulation_name": simulation_name,
                "capabilities": ["particle_dynamics", "quantum_field", "gravitational"],
                "metrics": self.metrics_cache.get(
                    simulation_name, SimulationMetrics(0, 0, 0, 0, 0, 0)
                ).__dict__,
            },
        )

        # Register with connection pool for distributed processing
        self.connection_pool.register_agent(
            agent.id,
            {
                "gpu_acceleration": True,
                "simulation_name": simulation_name,
                "resource_profile": agent.get_resource_profile(),
            },
        )


# Global instance for system-wide access
GPU_ACCELERATION_MANAGER = GPUAccelerationManager()


def get_gpu_acceleration_manager() -> GPUAccelerationManager:
    """Get the global GPU acceleration manager."""
    return GPU_ACCELERATION_MANAGER
