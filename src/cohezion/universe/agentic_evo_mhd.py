"""
Agentic EVO with MHD (Magnetohydrodynamics)

Extends AgenticEVO to include:
- Magnetic fields (B) in physical space
- Plasma dynamics (ionized EVOs)
- MHD coupling to FLUME latent space

New concepts:
- Magnetic coherence: alignment of B-field with latent structure
- Plasma agents: EVOs with ionization states
- Alfven waves: magnetic information propagation
- Reconnection: topological changes in field lines
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# Import base EVO classes
from cohezion.universe.agentic_evo_swift import (
    AgenticEVO,
)


class IonizationState(Enum):
    """
    Plasma ionization states for EVOs.

    Couples to MHD dynamics and latent coherence.
    """

    NEUTRAL = 0  # No ionization, no MHD
    PARTIALLY_IONIZED = 0.5  # Two-fluid effects
    FULLY_IONIZED = 1.0  # Ideal MHD regime
    EXOTIC_PLASMA = -1.0  # Negative ionization (exotic)
    QUANTUM_DEGENERATE = 2.0  # High density, quantum effects


@dataclass
class EVOMagneticState:
    """
    Magnetic field state for an EVO agent.

    Represents local B-field sourced by the agent and
    its magnetic moment in the latent space.
    """

    agent_id: str

    # Physical magnetic field (Gauss or Tesla)
    B_field: np.ndarray = field(default_factory=lambda: np.zeros(3))
    B_magnitude: float = 0.0

    # Latent space magnetic coherence
    # 256D representation of magnetic topology
    magnetic_latent: np.ndarray = field(default_factory=lambda: np.zeros(256))

    # Plasma properties
    ionization_fraction: float = 0.0  # 0 to 1
    ionization_state: IonizationState = IonizationState.NEUTRAL
    electron_density: float = 0.0  # cm^-3
    temperature: float = 0.0  # Kelvin

    # MHD parameters
    plasma_beta: float = 1.0  # P_thermal / P_magnetic
    alfven_speed: float = 0.0
    magnetic_reynolds: float = 0.0  # Rm = UL/η

    # Divergence cleaning (maintain ∇·B = 0)
    div_b_error: float = 0.0

    def compute_alfven_speed(self, density: float) -> float:
        """v_A = B / sqrt(4πρ) in CGS, or B / sqrt(μ₀ρ) in SI."""
        if density <= 0:
            return 0.0
        return np.linalg.norm(self.B_field) / np.sqrt(density)

    def compute_plasma_beta(self, thermal_pressure: float) -> float:
        """β = 8πP/B², ratio of thermal to magnetic pressure."""
        b_sq = np.sum(self.B_field**2)
        if b_sq <= 0:
            return float("inf")
        return 8 * np.pi * thermal_pressure / b_sq


@dataclass
class MHDField:
    """
    Grid-based MHD field for global magnetic topology.

    Represents the cosmic magnetic field in which EVOs evolve.
    """

    grid_size: tuple[int, int, int] = (64, 64, 64)
    box_size: float = 1000.0  # Physical size in Mpc or kpc

    # Vector field components
    Bx: np.ndarray = field(init=False)
    By: np.ndarray = field(init=False)
    Bz: np.ndarray = field(init=False)

    # Derived fields
    divB: np.ndarray = field(init=False)  # Divergence error
    current_density: np.ndarray = field(init=False)  # J = ∇ × B

    def __post_init__(self):
        nx, ny, nz = self.grid_size
        self.Bx = np.zeros((nx, ny, nz))
        self.By = np.zeros((nx, ny, nz))
        self.Bz = np.zeros((nx, ny, nz))
        self.divB = np.zeros((nx, ny, nz))
        self.current_density = np.zeros((nx, ny, nz, 3))

    def get_b_vector(self, ix: int, iy: int, iz: int) -> np.ndarray:
        """Get B field at grid point."""
        return np.array([self.Bx[ix, iy, iz], self.By[ix, iy, iz], self.Bz[ix, iy, iz]])

    def set_b_vector(self, ix: int, iy: int, iz: int, b: np.ndarray):
        """Set B field at grid point."""
        self.Bx[ix, iy, iz] = b[0]
        self.By[ix, iy, iz] = b[1]
        self.Bz[ix, iy, iz] = b[2]

    def compute_divergence(self) -> float:
        """Compute ∇·B across grid using finite differences."""
        nx, _ny, _nz = self.grid_size
        dx = self.box_size / nx

        # Central differences for interior points
        dBx_dx = (np.roll(self.Bx, -1, axis=0) - np.roll(self.Bx, 1, axis=0)) / (2 * dx)
        dBy_dy = (np.roll(self.By, -1, axis=1) - np.roll(self.By, 1, axis=1)) / (2 * dx)
        dBz_dz = (np.roll(self.Bz, -1, axis=2) - np.roll(self.Bz, 1, axis=2)) / (2 * dx)

        self.divB = dBx_dx + dBy_dy + dBz_dz
        return np.max(np.abs(self.divB))

    def compute_curl(self) -> np.ndarray:
        """Compute ∇ × B (current density in units where μ₀ = 4π)."""
        nx, _ny, _nz = self.grid_size
        dx = self.box_size / nx

        # ∂Bz/∂y - ∂By/∂z
        dBz_dy = (np.roll(self.Bz, -1, axis=1) - np.roll(self.Bz, 1, axis=1)) / (2 * dx)
        dBy_dz = (np.roll(self.By, -1, axis=2) - np.roll(self.By, 1, axis=2)) / (2 * dx)
        Jx = dBz_dy - dBy_dz

        # ∂Bx/∂z - ∂Bz/∂x
        dBx_dz = (np.roll(self.Bx, -1, axis=2) - np.roll(self.Bx, 1, axis=2)) / (2 * dx)
        dBz_dx = (np.roll(self.Bz, -1, axis=0) - np.roll(self.Bz, 1, axis=0)) / (2 * dx)
        Jy = dBx_dz - dBz_dx

        # ∂By/∂x - ∂Bx/∂y
        dBy_dx = (np.roll(self.By, -1, axis=0) - np.roll(self.By, 1, axis=0)) / (2 * dx)
        dBx_dy = (np.roll(self.Bx, -1, axis=1) - np.roll(self.Bx, 1, axis=1)) / (2 * dx)
        Jz = dBy_dx - dBx_dy

        self.current_density = np.stack([Jx, Jy, Jz], axis=-1)
        return self.current_density


class AgenticEVOMHD(AgenticEVO):
    """
    Agentic EVO with MHD capabilities.

    Extends base EVO with:
    - Magnetic field generation
    - Plasma dynamics
    - Alfven wave coupling to latent space
    """

    def __init__(
        self, agent_id: str, initial_latent: np.ndarray | None = None, magnetic_moment: float = 1.0
    ):
        super().__init__(agent_id, initial_latent)

        # Magnetic state
        self.magnetic_state = EVOMagneticState(
            agent_id=agent_id,
            B_field=np.random.randn(3) * 0.01,  # Random small field
        )

        # Plasma properties
        self.magnetic_moment = magnetic_moment
        self.ionization_threshold = 0.5  # Coherence threshold for ionization

        # MHD coupling strength
        self.latent_magnetic_coupling = 0.01  # How much B affects latent
        self.magnetic_latent_coupling = 0.01  # How much latent affects B

    def update_ionization(self):
        """
        Update plasma ionization based on latent coherence.

        High coherence agents become fully ionized plasma.
        Low coherence remain neutral.
        Exotic agents have exotic ionization.
        """
        coherence = self.latent_state.current_coherence

        if self.latent_state.is_exotic:
            if self.latent_state.exotic_type == "negative_mass":
                self.magnetic_state.ionization_state = IonizationState.EXOTIC_PLASMA
                self.magnetic_state.ionization_fraction = -0.5
            else:
                self.magnetic_state.ionization_state = IonizationState.QUANTUM_DEGENERATE
                self.magnetic_state.ionization_fraction = 1.5
        else:
            # Standard ionization based on coherence (analogous to temperature)
            if coherence > 0.7:
                self.magnetic_state.ionization_state = IonizationState.NEUTRAL
                self.magnetic_state.ionization_fraction = 0.0
            elif coherence > 0.4:
                self.magnetic_state.ionization_state = IonizationState.PARTIALLY_IONIZED
                self.magnetic_state.ionization_fraction = 0.5
            else:
                self.magnetic_state.ionization_state = IonizationState.FULLY_IONIZED
                self.magnetic_state.ionization_fraction = 1.0

        # Temperature from coherence (analogy: latent energy = thermal energy)
        self.magnetic_state.temperature = 1e4 * (1.1 - coherence)  # Kelvin

    def generate_magnetic_field(self):
        """
        Generate B-field from latent structure.

        Idea: Complexity in latent space sources magnetic field.
        High information content = strong field.
        """
        # Compute latent gradient (direction of steepest change)
        if len(self.latent_state.journey_positions) >= 2:
            latent_velocity = (
                self.latent_state.journey_positions[-1] - self.latent_state.journey_positions[-2]
            )
        else:
            latent_velocity = np.zeros(256)

        # Project 256D latent motion to 3D physical B-field
        # Simplified: use first 3 principal components
        b_direction = np.array(
            [
                np.mean(latent_velocity[0:85]),
                np.mean(latent_velocity[85:170]),
                np.mean(latent_velocity[170:256]),
            ]
        )

        # Normalize
        b_norm = np.linalg.norm(b_direction)
        if b_norm > 1e-10:
            b_direction /= b_norm

        # Field strength from coherence and information
        b_strength = (
            self.latent_state.information_content
            * (1.0 - self.latent_state.current_coherence)
            * self.magnetic_moment
        )

        self.magnetic_state.B_field = b_direction * b_strength
        self.magnetic_state.B_magnitude = b_strength

    def compute_lorentz_force(self) -> np.ndarray:
        """
        F_L = J × B (Lorentz force from currents and field).

        Simplified: F = (∇ × B) × B / 4π in CGS
        """
        B = self.magnetic_state.B_field

        # Approximate current from curl (need field gradient)
        # Simplified: use stored current density
        J = (
            self.magnetic_state.current_density
            if hasattr(self.magnetic_state, "current_density")
            else np.zeros(3)
        )

        # F = J × B
        F = np.cross(J, B)
        return F

    def alfven_wave_coupling(self, dt: float, global_b_field: np.ndarray):
        """
        Couple agent to Alfven waves in global magnetic field.

        Alfven waves propagate information along B-field lines,
        causing correlations in agent journeys.
        """
        b_unit = global_b_field / (np.linalg.norm(global_b_field) + 1e-10)

        # Project latent velocity onto B-field direction
        latent_v = np.zeros(256)
        if len(self.latent_state.journey_positions) >= 2:
            latent_v = (
                self.latent_state.journey_positions[-1] - self.latent_state.journey_positions[-2]
            ) / dt

        # Parallel component propagates
        parallel_factor = np.sum(latent_v[:3] * b_unit)

        # Alfven coupling: align latent evolution with B-field
        self.latent_state.latent_vector += (
            self.latent_magnetic_coupling
            * parallel_factor
            * np.tile(b_unit, 86)[:256]  # Broadcast to 256D
        )

    def magnetic_reconnection(self, other: AgenticEVOMHD) -> bool:
        """
        Model magnetic reconnection between two EVOs.

        Occurs when oppositely directed B-fields come close.
        Releases energy, causes rapid state changes.

        Returns:
            True if reconnection occurred
        """
        # Distance check
        r_vec = other.physical_state.position - self.physical_state.position
        r_mag = np.linalg.norm(r_vec)

        # Reconnection distance
        reconnect_dist = 10.0  # arbitrary units

        if r_mag > reconnect_dist:
            return False

        # Check anti-parallel fields
        b1 = self.magnetic_state.B_field
        b2 = other.magnetic_state.B_field

        if np.linalg.norm(b1) < 1e-10 or np.linalg.norm(b2) < 1e-10:
            return False

        # Dot product < 0 means anti-parallel
        alignment = np.dot(b1 / np.linalg.norm(b1), b2 / np.linalg.norm(b2))

        if alignment > -0.5:
            return False  # Fields not anti-parallel enough

        # Reconnection occurs!
        # Release energy: increase information content
        energy_release = np.linalg.norm(b1) * np.linalg.norm(b2) / (r_mag + 1.0)

        self.latent_state.information_content += energy_release
        other.latent_state.information_content += energy_release

        # Flip fields (simplified model)
        self.magnetic_state.B_field *= -0.5
        other.magnetic_state.B_field *= -0.5

        return True

    def hiho_step_mhd(
        self,
        delta_scale: float = 0.01,
        hiho_damping: float = 0.05,
        global_b_field: np.ndarray | None = None,
    ):
        """
        Extended HIHO step with MHD effects.

        Adds:
        - Alfven wave propagation
        - Lorentz force on latent evolution
        - Magnetic pressure effects
        """
        # Standard HIHO
        super().hiho_step(delta_scale, hiho_damping)

        # Update plasma state
        self.update_ionization()

        # Generate B-field from latent structure
        self.generate_magnetic_field()

        # MHD coupling
        if global_b_field is not None:
            self.alfven_wave_coupling(0.01, global_b_field)

        # Lorentz force feedback
        lorentz = self.compute_lorentz_force()
        # Convert physical force to latent perturbation
        lorentz_latent = np.tile(lorentz, 86)[:256] * self.magnetic_latent_coupling
        self.latent_state.latent_vector += lorentz_latent


class AgenticMHDSystem:
    """
    Full MHD system with Agentic EVOs in plasma.

    Combines:
    - Particle-based EVO agents (Lagrangian)
    - Grid-based MHD fields (Eulerian)
    - Bidirectional coupling
    """

    def __init__(
        self,
        n_evos: int = 100,
        grid_size: tuple[int, int, int] = (32, 32, 32),
        box_size: float = 1000.0,
    ):
        self.n_evos = n_evos
        self.box_size = box_size

        # MHD field
        self.mhd_field = MHDField(grid_size=grid_size, box_size=box_size)

        # EVO agents (with MHD)
        self.evos: list[AgenticEVOMHD] = []
        self._initialize_evos()

        # Simulation state
        self.timestep = 0
        self.time = 0.0

    def _initialize_evos(self):
        """Initialize MHD-capable EVOs."""
        for i in range(self.n_evos):
            is_exotic = np.random.random() < 0.15
            magnetic_moment = np.random.exponential(1.0)

            evo = AgenticEVOMHD(
                agent_id=f"EVO_MHD_{i:04d}",
                magnetic_moment=magnetic_moment,
            )

            if is_exotic:
                evo.latent_state.is_exotic = True
                evo.latent_state.exotic_type = np.random.choice(["repeller", "negative_mass"])

            # Initial B-field from latent structure
            evo.generate_magnetic_field()

            self.evos.append(evo)

    def deposit_b_to_grid(self):
        """
        Deposit agent B-fields to MHD grid (particle-to-grid).

        Uses cloud-in-cell or similar weighting.
        """
        nx, ny, nz = self.mhd_field.grid_size
        dx = self.box_size / nx

        # Clear grid
        self.mhd_field.Bx.fill(0)
        self.mhd_field.By.fill(0)
        self.mhd_field.Bz.fill(0)

        # Deposit from particles
        for evo in self.evos:
            pos = evo.physical_state.position
            b = evo.magnetic_state.B_field

            # Find cell
            ix = int(pos[0] / dx) % nx
            iy = int(pos[1] / dx) % ny
            iz = int(pos[2] / dx) % nz

            # Add to cell (simple nearest-grid-point)
            self.mhd_field.Bx[ix, iy, iz] += b[0]
            self.mhd_field.By[ix, iy, iz] += b[1]
            self.mhd_field.Bz[ix, iy, iz] += b[2]

        # Normalize by number density (simplified)
        for evo in self.evos:
            pos = evo.physical_state.position
            ix = int(pos[0] / dx) % nx
            iy = int(pos[1] / dx) % ny
            iz = int(pos[2] / dx) % nz

            # Count particles in cell
            count = sum(
                1
                for e in self.evos
                if (
                    int(e.physical_state.position[0] / dx) % nx == ix
                    and int(e.physical_state.position[1] / dx) % ny == iy
                    and int(e.physical_state.position[2] / dx) % nz == iz
                )
            )

            if count > 0:
                self.mhd_field.Bx[ix, iy, iz] /= count
                self.mhd_field.By[ix, iy, iz] /= count
                self.mhd_field.Bz[ix, iy, iz] /= count

    def interpolate_b_to_particles(self):
        """
        Interpolate grid B-field to agent positions (grid-to-particle).
        """
        nx, ny, nz = self.mhd_field.grid_size
        dx = self.box_size / nx

        for evo in self.evos:
            pos = evo.physical_state.position

            ix = int(pos[0] / dx) % nx
            iy = int(pos[1] / dx) % ny
            iz = int(pos[2] / dx) % nz

            # Nearest neighbor (could be CIC for smoother)
            b_at_pos = self.mhd_field.get_b_vector(ix, iy, iz)

            # Update agent's perceived field
            # (Real field is sum of self-generated + external)
            evo.magnetic_state.B_field = (
                0.7 * evo.magnetic_state.B_field  # Persistent self-field
                + 0.3 * b_at_pos  # External field
            )

    def step(self, dt: float = 0.01):
        """
        Full MHD timestep.

        Sequence:
        1. Deposit B-fields to grid
        2. Compute MHD derivatives (curl, divergence)
        3. Interpolate back to particles
        4. Evolve EVOs with MHD
        5. Handle reconnection
        6. Physical N-body step
        """
        # Phase 1: Deposit B to grid
        self.deposit_b_to_grid()

        # Phase 2: Compute MHD field derivatives
        max_div_b = self.mhd_field.compute_divergence()
        self.mhd_field.compute_curl()

        # Phase 3: Interpolate to particles
        self.interpolate_b_to_particles()

        # Phase 4: Evolve each EVO with MHD
        global_b = np.array(
            [np.mean(self.mhd_field.Bx), np.mean(self.mhd_field.By), np.mean(self.mhd_field.Bz)]
        )

        for evo in self.evos:
            evo.hiho_step_mhd(global_b_field=global_b)

        # Phase 5: Reconnection detection
        reconnection_count = 0
        for i, evo_i in enumerate(self.evos):
            for _j, evo_j in enumerate(self.evos[i + 1 :], start=i + 1):
                if evo_i.magnetic_reconnection(evo_j):
                    reconnection_count += 1

        # Phase 6: Physical dynamics (simplified N-body)
        self._physical_step(dt)

        self.timestep += 1
        self.time += dt

        return {
            "max_div_b": max_div_b,
            "reconnections": reconnection_count,
            "mean_b": np.linalg.norm(global_b),
        }

    def _physical_step(self, dt: float):
        """Simplified N-body with MHD forces."""
        np.array([e.physical_state.position for e in self.evos])
        masses = np.array([e.physical_state.effective_mass for e in self.evos])

        for i, evo_i in enumerate(self.evos):
            force = np.zeros(3)

            # Gravity
            for j, evo_j in enumerate(self.evos):
                if i == j:
                    continue
                r_vec = evo_j.physical_state.position - evo_i.physical_state.position
                r_mag = np.linalg.norm(r_vec) + 1e-10

                # Gravity (with exotic repulsion)
                if masses[i] < 0 or masses[j] < 0:
                    force_mag = -masses[i] * masses[j] / (r_mag**2)
                else:
                    force_mag = masses[i] * masses[j] / (r_mag**2)

                force += force_mag * r_vec / r_mag

            # Lorentz force
            force += evo_i.compute_lorentz_force()

            # Update
            acceleration = force / (abs(masses[i]) + 1e-10)
            evo_i.physical_state.velocity += acceleration * dt
            evo_i.physical_state.position += evo_i.physical_state.velocity * dt

    def get_mhd_statistics(self) -> dict:
        """MHD-specific statistics."""
        ionized_count = sum(
            1
            for e in self.evos
            if e.magnetic_state.ionization_state
            in [IonizationState.PARTIALLY_IONIZED, IonizationState.FULLY_IONIZED]
        )

        exotic_plasma = sum(
            1
            for e in self.evos
            if e.magnetic_state.ionization_state == IonizationState.EXOTIC_PLASMA
        )

        mean_b = np.mean([e.magnetic_state.B_magnitude for e in self.evos])
        mean_beta = np.mean([e.magnetic_state.plasma_beta for e in self.evos])

        return {
            "timestep": self.timestep,
            "time": self.time,
            "n_evos": self.n_evos,
            "ionized": ionized_count,
            "exotic_plasma": exotic_plasma,
            "mean_b_field": mean_b,
            "mean_plasma_beta": mean_beta,
            "max_div_b_error": np.max(np.abs(self.mhd_field.divB)),
        }


def demo_mhd_simulation():
    """Demonstrate MHD EVO simulation."""
    print("=" * 70)
    print("AGENTIC EVO WITH MHD (Magnetohydrodynamics)")
    print("Coupling: FLUME↔MHD Fields↔Plasma Dynamics")
    print("=" * 70)

    print("\nInitializing 50 MHD-EVOs on 32³ grid...")
    system = AgenticMHDSystem(n_evos=50, grid_size=(32, 32, 32), box_size=100.0)

    # Show initial state
    stats = system.get_mhd_statistics()
    print(f"  Standard: {stats['n_evos'] - stats['ionized'] - stats['exotic_plasma']}")
    print(f"  Plasma (ionized): {stats['ionized']}")
    print(f"  Exotic plasma: {stats['exotic_plasma']}")
    print(f"  Initial mean |B|: {stats['mean_b_field']:.4f}")

    # Run simulation
    print("\nRunning 50 MHD timesteps...")
    print("Tracking: Div B errors, Reconnections, Plasma states")

    for step in range(50):
        mhd_info = system.step(dt=0.01)

        if step % 10 == 0:
            stats = system.get_mhd_statistics()
            print(
                f"  Step {step}: DivB={mhd_info['max_div_b']:.2e}, "
                f"Rc={mhd_info['reconnections']}, "
                f"<B>={stats['mean_b_field']:.3f}, "
                f"β={stats['mean_plasma_beta']:.2f}"
            )

    # Final stats
    print("\n" + "=" * 70)
    print("FINAL MHD STATISTICS")
    print("=" * 70)

    stats = system.get_mhd_statistics()
    print(f"Timesteps: {stats['timestep']}")
    print("Final plasma states:")
    print(
        f"  Neutral: {sum(1 for e in system.evos if e.magnetic_state.ionization_state == IonizationState.NEUTRAL)}"
    )
    print(
        f"  Partially ionized: {sum(1 for e in system.evos if e.magnetic_state.ionization_state == IonizationState.PARTIALLY_IONIZED)}"
    )
    print(
        f"  Fully ionized: {sum(1 for e in system.evos if e.magnetic_state.ionization_state == IonizationState.FULLY_IONIZED)}"
    )
    print(f"  Exotic plasma: {stats['exotic_plasma']}")
    print("\nMagnetic field statistics:")
    print(f"  Mean |B|: {stats['mean_b_field']:.4f}")
    print(f"  Mean plasma β: {stats['mean_plasma_beta']:.2f}")
    print(f"  Max ∇·B error: {stats['max_div_b_error']:.2e}")

    print("\n" + "=" * 70)
    print("MHD SIMULATION COMPLETE")
    print("=" * 70)
    print("\nTo couple with SWIFT:")
    print("  1. Export B-field grid to SWIFT MHD ICs")
    print("  2. Include ionization fractions in particle data")
    print("  3. Run with --mhd flag in SWIFT")

    return system


if __name__ == "__main__":
    demo_mhd_simulation()
