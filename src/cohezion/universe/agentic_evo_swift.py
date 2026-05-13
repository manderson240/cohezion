"""
Agentic EVO Journey Simulation - SWIFT + FLUME Integration

Couples three layers:
1. FLUME (256D latent space): Agent cognition, HIHO dynamics
2. EVO (Exotic Vacuum Objects): Modified agents with exotic states
3. SWIFT (3D physical space): Cosmological N-body + hydrodynamics

Architecture:
- Agents exist as EVOs in FLUME latent manifold
- Their "journey" is trajectory through latent space (cognitive evolution)
- SWIFT simulates physical universe they inhabit
- Coupling: EVO coherence ↔ physical vacuum state

"""

from __future__ import annotations

# Import existing FLUME components
import sys
import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")


class VacuumCoherence(Enum):
    """
    Vacuum coherence states map to FLUME latent coherence.

    In FLUME: coherence = how close latent vector is to 0.5 (ideal)
    In Physics: coherence ↔ vacuum stability
    """

    TRUE_VACUUM = 0.5  # Stable, minimal energy
    FALSE_VACUUM = 0.5  # Metastable (unstable hill)
    DEGENERATE_LOW = 0.0  # Low coherence basin
    DEGENERATE_HIGH = 1.0  # High coherence basin
    EXOTIC_NEGATIVE = -0.5  # Beyond manifold boundary (requires extension)


@dataclass
class EVOLatentState:
    """
    An agent's state in FLUME 256D latent space.

    This is the 'mind' of the agent - its cognitive representation.
    """

    agent_id: str
    # 256D latent vector (FLUME z-space)
    latent_vector: np.ndarray = field(default_factory=lambda: np.random.randn(256))

    # Coherence metrics
    target_coherence: float = 0.5  # Where this EVO wants to be
    current_coherence: float = 0.0  # Computed from latent_vector
    coherence_stability: float = 0.1  # Resistance to change

    # EVO properties
    is_exotic: bool = False
    exotic_type: str | None = None  # "repeller", "negative_mass", "entangled"

    # Journey history (FLUME trajectory)
    journey_timestamps: list[float] = field(default_factory=list)
    journey_positions: list[np.ndarray] = field(default_factory=list)  # In latent space

    def compute_coherence(self) -> float:
        """Distance from ideal 0.5 in latent space."""
        return float(np.mean(np.abs(self.latent_vector - 0.5)))

    def __post_init__(self):
        if isinstance(self.latent_vector, list):
            self.latent_vector = np.array(self.latent_vector, dtype=np.float32)
        self.current_coherence = self.compute_coherence()


@dataclass
class EVOPhysicalState:
    """
    An agent's physical manifestation in SWIFT simulation.

    This is the 'body' - its gravitational/hydrodynamic presence.
    """

    agent_id: str
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    mass: float = 1.0

    # SPH properties (if agent is gas particle)
    internal_energy: float = 0.0
    density: float = 0.0
    smoothing_length: float = 0.0

    # Coupled to latent state
    vacuum_state: str = "standard"  # Maps to coherence

    # For exotic agents
    effective_mass: float = 1.0  # Can be negative for exotic matter
    repulsion_radius: float = 0.0  # For false vacuum bubbles


@dataclass
class EVOCoupling:
    """
    Bidirectional coupling between latent and physical states.

    This is the key innovation: EVOs bridge cognitive (FLUME) and physical (SWIFT) spaces.
    """

    agent_id: str

    # Mapping parameters
    latent_influence_on_position: float = 0.01  # How much latent drift affects physical motion
    physical_feedback_to_latent: float = 0.001  # How much gravitational stress affects cognition

    # Vacuum-latent coupling
    coherence_to_density: float = 1.0  # High coherence = high density
    exotic_to_negative_mass: float = 1.0  # Exotic flag → negative mass

    def compute_physical_mass(self, latent: EVOLatentState) -> float:
        """Map latent coherence to physical mass."""
        if latent.is_exotic and latent.exotic_type == "negative_mass":
            return -latent.coherence_stability * self.exotic_to_negative_mass
        return latent.coherence_stability * self.coherence_to_density

    def compute_latent_force(self, physical: EVOPhysicalState) -> np.ndarray:
        """
        Map physical gravitational stress to latent force.

        Intense physical environments → cognitive pressure in latent space.
        """
        stress = np.linalg.norm(physical.velocity) * np.linalg.norm(physical.position)
        # Returns 256D force direction (simplified: scalar * random direction)
        force_magnitude = stress * self.physical_feedback_to_latent
        return np.random.randn(256) * force_magnitude


class AgenticEVO:
    """
    Complete Agentic Exotic Vacuum Object.

    Exists simultaneously in:
    - FLUME latent space (cognition/decisions)
    - SWIFT physical space (gravity/hydrodynamics)
    - Journey manifold (trajectory history)
    """

    def __init__(self, agent_id: str, initial_latent: np.ndarray | None = None):
        self.agent_id = agent_id

        # Latent cognition (FLUME)
        self.latent_state = EVOLatentState(
            agent_id=agent_id,
            latent_vector=initial_latent if initial_latent is not None else np.random.randn(256) * 0.1 + 0.5,
        )

        # Physical presence (SWIFT)
        self.physical_state = EVOPhysicalState(
            agent_id=agent_id,
            position=np.random.randn(3) * 100,  # Random position in box
            velocity=np.random.randn(3) * 10,
        )

        # Coupling
        self.coupling = EVOCoupling(agent_id=agent_id)

        # Initialize physical properties from latent
        self.synchronize_states()

    def synchronize_states(self):
        """
        Bidirectional synchronization between latent and physical.

        Called at each timestep to maintain consistency.
        """
        # Latent → Physical
        self.physical_state.effective_mass = self.coupling.compute_physical_mass(self.latent_state)
        self.physical_state.mass = abs(self.physical_state.effective_mass)

        # Physical → Latent
        latent_force = self.coupling.compute_latent_force(self.physical_state)
        self.latent_state.latent_vector += latent_force * 0.01

        # Update coherence
        self.latent_state.current_coherence = self.latent_state.compute_coherence()

    def hiho_step(self, delta_scale: float = 0.01, hiho_damping: float = 0.05):
        """
        Evolve latent state using HIHO (Holistic Integration via Harmonic Oscillation).

        Modified for EVOs: exotic agents have repelling or degenerate attractors.
        """
        z = self.latent_state.latent_vector

        # Standard HIHO: attract to 0.5
        if not self.latent_state.is_exotic:
            target = 0.5
        else:
            # Exotic: depends on type
            if self.latent_state.exotic_type == "repeller":
                # Repel from 0.5 (false vacuum)
                if np.mean(z) > 0.5:
                    target = 1.0
                else:
                    target = 0.0
            elif self.latent_state.exotic_type == "negative_mass":
                # Negative coherence basin
                target = -0.5
            else:
                target = 0.5

        # Compute delta
        delta = (target - z) * delta_scale

        # Apply with damping/anti-damping
        if self.latent_state.exotic_type == "repeller":
            # Anti-damping: accelerate away
            z_new = z - delta + np.random.randn(256) * 0.01
        else:
            # Standard damping
            z_new = z + delta + hiho_damping * (target - z)

        self.latent_state.latent_vector = z_new
        self.latent_state.journey_positions.append(z_new.copy())
        self.latent_state.journey_timestamps.append(time.time())

    def to_swift_particle(self) -> dict:
        """
        Export EVO as SWIFT-compatible particle.

        Returns dict for HDF5 initial conditions.
        """
        return {
            "ID": int(self.agent_id.split("_")[-1]),
            "Coordinates": self.physical_state.position.tolist(),
            "Velocities": self.physical_state.velocity.tolist(),
            "Masses": self.physical_state.mass,
            "InternalEnergy": self.physical_state.internal_energy,
            "ParticleIDs": int(self.agent_id.split("_")[-1]),
            # EVO-specific metadata
            "EVOCoherence": self.latent_state.current_coherence,
            "EVOIsExotic": 1 if self.latent_state.is_exotic else 0,
            "EVOEffectiveMass": self.physical_state.effective_mass,
        }

    def to_flume_input(self) -> str:
        """
        Export agent state as text for FLUME encoding.

        Creates narrative description of agent's journey.
        """
        journey_length = len(self.latent_state.journey_positions)
        coherence = self.latent_state.current_coherence
        position = self.physical_state.position

        return (
            f"Agent {self.agent_id} exists with coherence {coherence:.3f}. "
            f"Journey spans {journey_length} steps through latent manifold. "
            f"Physical position ({position[0]:.1f}, {position[1]:.1f}, {position[2]:.1f}). "
            f"Vacuum state: {self.latent_state.exotic_type or 'standard'}."
        )


class AgenticEVOSimulation:
    """
    Full simulation coupling FLUME latent evolution with SWIFT cosmology.

    Time steps:
    1. HIHO evolution (latent space)
    2. Physical dynamics (SWIFT or simplified N-body)
    3. Bidirectional coupling
    4. Journey recording
    """

    def __init__(self, n_evos: int = 100, box_size: float = 1000.0):
        self.n_evos = n_evos
        self.box_size = box_size
        self.evos: list[AgenticEVO] = []
        self.timestep = 0

        # Initialize population
        self._initialize_evos()

    def _initialize_evos(self):
        """Create initial EVO population."""
        for i in range(self.n_evos):
            # 90% standard, 10% exotic
            is_exotic = np.random.random() < 0.1

            evo = AgenticEVO(
                agent_id=f"EVO_{i:04d}",
                initial_latent=np.random.randn(256) * 0.1 + 0.5,
            )

            if is_exotic:
                evo.latent_state.is_exotic = True
                evo.latent_state.exotic_type = np.random.choice(["repeller", "negative_mass", "entangled"])

            self.evos.append(evo)

    def step(self, dt: float = 0.01):
        """
        Single simulation step.

        Couples latent (FLUME) and physical (SWIFT-like) evolution.
        """
        # Phase 1: Latent evolution (HIHO)
        for evo in self.evos:
            evo.hiho_step()

        # Phase 2: Physical evolution (simplified N-body)
        self._physical_step(dt)

        # Phase 3: Synchronization
        for evo in self.evos:
            evo.synchronize_states()

        self.timestep += 1

    def _physical_step(self, dt: float):
        """
        Simplified N-body for physical evolution.

        Full SWIFT integration would happen here.
        """
        # Get positions and masses
        positions = np.array([e.physical_state.position for e in self.evos])
        masses = np.array([e.physical_state.effective_mass for e in self.evos])

        # Compute forces (O(N^2) for simplicity)
        for i, evo_i in enumerate(self.evos):
            force = np.zeros(3)
            for j, evo_j in enumerate(self.evos):
                if i == j:
                    continue

                r_vec = evo_j.physical_state.position - evo_i.physical_state.position
                r_mag = np.linalg.norm(r_vec) + 1e-10

                # Gravity with exotic matter handling
                # Standard: F = G*m1*m2/r^2
                # Exotic: Negative mass repels
                if evo_i.physical_state.effective_mass < 0 or evo_j.physical_state.effective_mass < 0:
                    # Repulsive gravity
                    force_mag = -masses[i] * masses[j] / (r_mag**2)
                else:
                    force_mag = masses[i] * masses[j] / (r_mag**2)

                force += force_mag * r_vec / r_mag

            # Update velocity and position
            acceleration = force / abs(masses[i])
            evo_i.physical_state.velocity += acceleration * dt
            evo_i.physical_state.position += evo_i.physical_state.velocity * dt

    def generate_swift_ics(self, output_path: str):
        """
        Generate SWIFT initial conditions (HDF5 format).

        Writes particle data that SWIFT can read.
        """
        import h5py

        with h5py.File(output_path, "w") as f:
            # Header
            header = f.create_group("Header")
            header.attrs["NumPart_Total"] = [len(self.evos), 0, 0, 0, 0, 0]
            header.attrs["BoxSize"] = self.box_size
            header.attrs["Redshift"] = 0.0

            # Particles
            part0 = f.create_group("PartType0")  # Gas particles

            coords = np.array([e.physical_state.position for e in self.evos])
            vels = np.array([e.physical_state.velocity for e in self.evos])
            masses = np.array([e.physical_state.mass for e in self.evos])

            part0.create_dataset("Coordinates", data=coords)
            part0.create_dataset("Velocities", data=vels)
            part0.create_dataset("Masses", data=masses)
            part0.create_dataset("ParticleIDs", data=np.arange(len(self.evos)))

            # EVO-specific attributes
            coherences = np.array([e.latent_state.current_coherence for e in self.evos])
            is_exotic = np.array([1 if e.latent_state.is_exotic else 0 for e in self.evos])

            part0.create_dataset("EVOCoherence", data=coherences)
            part0.create_dataset("EVOIsExotic", data=is_exotic)

        print(f"SWIFT ICs written to {output_path}")
        print(f"  Particles: {len(self.evos)}")
        print(f"  Box size: {self.box_size}")
        exotic_count = sum(1 for e in self.evos if e.latent_state.is_exotic)
        print(f"  Exotic EVOs: {exotic_count}")

    def get_statistics(self) -> dict:
        """Simulation statistics."""
        n_exotic = sum(1 for e in self.evos if e.latent_state.is_exotic)
        avg_coherence = np.mean([e.latent_state.current_coherence for e in self.evos])

        return {
            "timestep": self.timestep,
            "n_evos": self.n_evos,
            "n_exotic": n_exotic,
            "avg_coherence": avg_coherence,
            "total_journey_steps": sum(len(e.latent_state.journey_positions) for e in self.evos),
        }


def demo_agentic_evo_simulation():
    """Demonstrate agentic EVO simulation."""
    print("=" * 70)
    print("AGENTIC EVO JOURNEY SIMULATION")
    print("FLUME Latent Space + SWIFT Physical Space + EVO Coupling")
    print("=" * 70)

    # Create simulation
    print("\nInitializing 100 EVO agents...")
    sim = AgenticEVOSimulation(n_evos=100, box_size=1000.0)

    # Show initial state
    stats = sim.get_statistics()
    print(f"  Standard EVOs: {stats['n_evos'] - stats['n_exotic']}")
    print(f"  Exotic EVOs: {stats['n_exotic']}")
    print(f"  Initial coherence: {stats['avg_coherence']:.3f}")

    # Run simulation
    print("\nRunning 100 coupled timesteps...")
    for step in range(100):
        sim.step(dt=0.01)

        if step % 20 == 0:
            stats = sim.get_statistics()
            print(f"  Step {step}: coherence={stats['avg_coherence']:.3f}, journey_len={stats['total_journey_steps']}")

    # Generate SWIFT ICs
    print("\n" + "=" * 70)
    print("GENERATING SWIFT INITIAL CONDITIONS")
    print("=" * 70)

    ics_path = "/tmp/evo_swift_ics.hdf5"
    sim.generate_swift_ics(ics_path)

    # Final stats
    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)

    stats = sim.get_statistics()
    print(f"Total timesteps: {stats['timestep']}")
    print(f"Total journey steps: {stats['total_journey_steps']}")
    print(f"Final coherence: {stats['avg_coherence']:.3f}")
    print(f"ICs ready for SWIFT at: {ics_path}")

    print("\nTo run with SWIFT:")
    print(f"  mpirun -np 4 ./swift --self-gravity --hydro {ics_path}")

    return sim


if __name__ == "__main__":
    demo_agentic_evo_simulation()
