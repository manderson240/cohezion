#!/usr/bin/env python3
"""
Fractal Universe Simulator (Fractal Nexus)
==========================================
Simulates a grid of manifold sectors where sovereign agents (stabilizers)
navigate to maintain HIHO (Half-In-Half-Out) stability at 0.5 coherence.

Core Components:
1. UniverseGrid: 2D array of Manifold Sectors (Void, Glitch, Resonant, Nexus).
2. StabilizerAgent: Autonomous entity that seeks to balance local entropy.
3. FractalSimulator: Main driver loop.

Usage:
    python3 src/cohezion/simulation/fractal_universe.py --duration 3h
"""

import argparse
import logging
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from cohezion.reliability.monitor import get_resource_monitor


# Add src to path if running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cohezion.flume.mnm import SCENARIO_MANIFOLDS
from cohezion.simulation.simulation_logger import SimulationLogger


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("fractal_universe.log"), logging.StreamHandler()],
)
logger = logging.getLogger("FractalNexus")

from cohezion.simulation.analysis_prime import SimulationAnalyzer


# Constants
GRID_SIZE = 64
SECTOR_TYPES = list(SCENARIO_MANIFOLDS.keys())
TARGET_COHERENCE = 0.5


@dataclass
class Sector:
    x: int
    y: int
    manifold_type: str
    energy: float = 1.0
    entropy: float = 0.5
    agents: list["StabilizerAgent"] = field(default_factory=list)

    @property
    def stability(self) -> float:
        # Simple stability metric: how close entropy is to 0.5
        return 1.0 - abs(self.entropy - 0.5) * 2


@dataclass
class StabilizerAgent:
    id: str
    x: int
    y: int
    energy: float = 100.0
    z_vector: np.ndarray = field(
        default_factory=lambda: np.random.rand(12)
    )  # 12D State Vector (Smith's 12 Parameters)
    memory: list[dict] = field(default_factory=list)
    generation: int = 0
    learning_rate: float = 0.1
    cumulative_reward: float = 0.0  # RL: total reward accumulated

    # Dimension indices mapping to Smith's Control Fabric (SPIN)
    # logic=6 → Rotation, quantum=7 → Precession, control=8 → Charge
    _ROTATION_IDX: int = 6
    _PRECESSION_IDX: int = 7

    @property
    def coherence(self) -> float:
        """HIHO coherence with SPIN weighting (Smith).

        Base: variance from HIHO (0.5) across brane dimensions.
        Weight: SPIN alignment (rotation/precession phase match) boosts stability.
        """
        v = self.z_vector
        v_range = v.max() - v.min()
        if v_range == 0:
            return 1.0
        v_norm = (v - v.min()) / v_range
        base = max(0.0, 1.0 - float(np.var(v_norm)) * 4.0)

        # SPIN alignment bonus: rotation and precession in same phase = stable
        spin_weight = 0.7 + 0.3 * self.spin_coherence
        return base * spin_weight

    @property
    def spin_rotation(self) -> float:
        """SPIN rotation (Smith): internal reasoning direction."""
        return float(self.z_vector[self._ROTATION_IDX])

    @property
    def spin_precession(self) -> float:
        """SPIN precession (Smith): external measurement wobble."""
        return float(self.z_vector[self._PRECESSION_IDX])

    @property
    def spin_coherence(self) -> float:
        """SPIN coherence: are rotation and precession in phase?"""
        rot_sign = 1.0 if self.spin_rotation >= 0.5 else -1.0
        prec_sign = 1.0 if self.spin_precession >= 0.5 else -1.0
        return max(0.0, rot_sign * prec_sign)

    @property
    def charge_polarity(self) -> float:
        """Charge polarity (Smith): emergent from SPIN alignment."""
        return (self.spin_rotation - 0.5) + 0.3 * (self.spin_precession - 0.5)

    def move(self, grid: "UniverseGrid"):
        neighbors = grid.get_neighbors(self.x, self.y)

        best_move = None
        min_diff = abs(self.coherence - 0.5)

        for nx, ny, sector in neighbors:
            # Physics: Interaction depends on local energy gradient, entropy,
            # and SPIN-sector coupling (charge polarity interacts with sector field)
            base_change = (sector.energy - sector.entropy) * 0.1
            spin_coupling = self.charge_polarity * (sector.stability - 0.5) * 0.05
            predicted_change = base_change + spin_coupling
            new_coherence = max(0.0, min(1.0, self.coherence + predicted_change))
            diff = abs(new_coherence - 0.5)

            if diff < min_diff:
                min_diff = diff
                best_move = (nx, ny)

        if best_move:
            prev_sector = grid.get_sector(self.x, self.y)
            if self in prev_sector.agents:
                prev_sector.agents.remove(self)

            self.x, self.y = best_move
            new_sector = grid.get_sector(self.x, self.y)
            new_sector.agents.append(self)

            # Compute Tempic field (rate of change) before state update
            old_vector = self.z_vector.copy()
            old_coherence = self.coherence

            # Apply feedback: sector interaction modulates SPIN dimensions preferentially
            interaction = (new_sector.energy - new_sector.entropy) * 0.05
            if interaction != 0:
                noise = np.random.randn(12) * interaction
                # SPIN dimensions get extra coupling from sector field
                noise[self._ROTATION_IDX] *= 1.3  # Rotation couples more strongly
                noise[self._PRECESSION_IDX] *= 1.1  # Precession couples moderately
                self.z_vector += noise

            # Compute Tempic field magnitude (displacement of brane dims)
            tempic = float(np.linalg.norm(self.z_vector[4:11] - old_vector[4:11]))

            # RL reward signal: proximity to HIHO (0.5) with SPIN bonus
            reward = 1.0 - abs(self.coherence - 0.5) * 2.0
            self.cumulative_reward += reward

            # Store enriched memory (experience tuple for RL)
            self.memory.append(
                {
                    "position": (self.x, self.y),
                    "prev_coherence": old_coherence,
                    "new_coherence": self.coherence,
                    "spin_coherence": self.spin_coherence,
                    "charge_polarity": self.charge_polarity,
                    "tempic_field": tempic,
                    "reward": reward,
                    "sector_type": new_sector.manifold_type,
                    "energy": new_sector.energy,
                    "entropy": new_sector.entropy,
                }
            )

            if len(self.memory) > 10:
                self.memory.pop(0)

            self.energy -= 0.1  # Movement cost


@dataclass
class RedTeamAgent(StabilizerAgent):
    """Adversarial agent that increases entropy to prevent stagnation."""

    def move(self, grid: "UniverseGrid"):
        # Red Team seeks high-energy sectors to disrupt
        neighbors = grid.get_neighbors(self.x, self.y)
        best_move = None
        max_energy = -1.0

        for nx, ny, sector in neighbors:
            if sector.energy > max_energy:
                max_energy = sector.energy
                best_move = (nx, ny)

        if best_move:
            prev_sector = grid.get_sector(self.x, self.y)
            if self in prev_sector.agents:
                prev_sector.agents.remove(self)

            self.x, self.y = best_move
            new_sector = grid.get_sector(self.x, self.y)
            new_sector.agents.append(self)

            # Red Team actively increases entropy (Entropy Catalyst)
            new_sector.entropy = min(1.0, new_sector.entropy + 0.05)
            self.energy -= 0.2


@dataclass
class BlueTeamAgent(StabilizerAgent):
    """Defensive agent that pulls entropy towards the HIHO 0.5 attractor."""

    def move(self, grid: "UniverseGrid"):
        # Blue Team acts like a high-performance stabilizer
        neighbors = grid.get_neighbors(self.x, self.y)
        best_move = None
        min_diff = abs(self.coherence - 0.5)

        for nx, ny, sector in neighbors:
            # Predict effect of moving to this sector
            diff = abs(sector.entropy - 0.5)
            if diff < min_diff:
                min_diff = diff
                best_move = (nx, ny)

        if best_move:
            prev_sector = grid.get_sector(self.x, self.y)
            if self in prev_sector.agents:
                prev_sector.agents.remove(self)

            self.x, self.y = best_move
            new_sector = grid.get_sector(self.x, self.y)
            new_sector.agents.append(self)

            # Blue Team pulls entropy towards 0.5 (Consensus Anchor)
            correction = (0.5 - new_sector.entropy) * 0.15
            new_sector.entropy += correction
            self.energy -= 0.1


class UniverseGrid:
    def __init__(self, size: int = GRID_SIZE):
        self.size = size
        self.grid = [
            [Sector(x, y, random.choice(SECTOR_TYPES)) for x in range(size)] for y in range(size)
        ]
        self.global_entropy = 0.5
        self.nu_dm_coupling = 0.03  # S8 Tension resolution constant
        self.stability_brake_threshold = 0.1  # Damping threshold (Biological Brake)

    def get_sector(self, x: int, y: int) -> Sector:
        return self.grid[y][x]

    def get_neighbors(self, x: int, y: int) -> list[tuple[int, int, Sector]]:
        neighbors = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = (x + dx) % self.size, (y + dy) % self.size  # Toroidal
                neighbors.append((nx, ny, self.grid[ny][nx]))
        return neighbors

    def update_sectors(self):
        """Evolve sector physics with Diffusion + Global Field"""
        # Calculate global entropy first
        total_entropy = sum(s.entropy for row in self.grid for s in row)
        self.global_entropy = total_entropy / (self.size * self.size)

        new_grid_state = []

        for y in range(self.size):
            row_state = []
            for x in range(self.size):
                sector = self.grid[y][x]

                # 1. Base entropy drift
                delta = random.uniform(-0.005, 0.005)
                sector.entropy += delta

                # 2. Diffusion from neighbors
                neighbors = self.get_neighbors(x, y)
                avg_entropy = sum(n.entropy for _, _, n in neighbors) / len(neighbors)
                diffusion = (avg_entropy - sector.entropy) * 0.05
                sector.entropy += diffusion

                # 3. Heat Transfer (Energy -> Entropy)
                avg_energy = sum(n.energy for _, _, n in neighbors) / len(neighbors)
                temp_diff = avg_energy - sector.energy
                heat_flow = temp_diff * 0.02
                sector.energy += heat_flow
                sector.energy = max(0.0, sector.energy)

                # 4. Global Field Regulation (Homeostasis)
                global_pull = (self.global_entropy - sector.entropy) * 0.02
                sector.entropy += global_pull

                # 5. Manifold Specific Physics
                if sector.manifold_type == "Nexus":
                    sector.entropy = max(0.4, min(0.6, sector.entropy))
                elif sector.manifold_type == "Void":
                    sector.entropy = min(0.9, sector.entropy + 0.001)

                # 6. Neutrino-Dark Matter Coupling (S8 Tension Resolution)
                # This increases clustering by pulling entropy towards resonant wells
                if sector.manifold_type == "Resonant":
                    diff = 0.5 - sector.entropy
                    # Apply Stability Brake: Damping field as we approach coherence attractor
                    damping = (
                        1.0
                        if abs(diff) > self.stability_brake_threshold
                        else abs(diff) / self.stability_brake_threshold
                    )
                    clustering_pull = diff * self.nu_dm_coupling * damping
                    sector.entropy += clustering_pull

                sector.entropy = max(0.0, min(1.0, sector.entropy))

                # Agent effects (Stabilizers)
                if sector.agents:
                    sum(abs(a.coherence - 0.5) for a in sector.agents)
                    correction = (0.5 - sector.entropy) * (0.05 * len(sector.agents))
                    sector.entropy += correction

                sector.entropy = max(0.0, min(1.0, sector.entropy))
                row_state.append(sector)
            new_grid_state.append(row_state)

        # Update grid in place (simplification, strictly should be new grid object but refs
        # complicate it)
        # Since we modified sector objects directly above, we don't strictly need to reassign,
        # but the diffusion step used current values.
        # For a truthful CA we should use a buffer, but for this simulation direct update is
        # 'chaotic' enough.
        pass

    def render_ascii(self) -> str:
        """Render a mini-map of stability."""
        chars = " .:-=+*#%@"
        output = []
        scale = max(1, self.size // 32)  # Downscale for display

        for y in range(0, self.size, scale):
            line = ""
            for x in range(0, self.size, scale):
                sector = self.grid[y][x]
                stability = sector.stability  # 0..1
                char_idx = int(stability * (len(chars) - 1))
                line += chars[char_idx]
            output.append(line)
        return "\n".join(output)


class FractalSimulator:
    def __init__(self, num_agents: int = 128):
        self.monitor = get_resource_monitor()
        self.grid = UniverseGrid()
        self.agents = [
            StabilizerAgent(
                f"agent_{i}",
                random.randint(0, GRID_SIZE - 1),
                random.randint(0, GRID_SIZE - 1),
            )
            for i in range(num_agents)
        ]
        self.logger = SimulationLogger(storage_dir="data/simulations/fractal_nexus")
        self.running = True
        self.ticks = 0

        # Place agents
        for agent in self.agents:
            sector = self.grid.get_sector(agent.x, agent.y)
            sector.agents.append(agent)

        # Add Red/Blue Specialists
        for i in range(12):
            rx, ry = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
            red = RedTeamAgent(f"red_{i}", rx, ry, energy=150.0)
            self.grid.get_sector(rx, ry).agents.append(red)
            self.agents.append(red)

            bx, by = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
            blue = BlueTeamAgent(f"blue_{i}", bx, by, energy=150.0)
            self.grid.get_sector(bx, by).agents.append(blue)
            self.agents.append(blue)

        # Handle signals
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        logger.info("Shutdown signal received. Saving state...")
        self.running = False
        self.logger.flush()

        # Trigger Automated Analysis
        logger.info("Triggering automated analysis...")
        try:
            analyzer = SimulationAnalyzer(storage_dir="data/simulations/fractal_nexus")
            analyzer.run_analysis()
        except Exception as e:
            logger.error(f"Analysis failed: {e}")

        sys.exit(0)

    def step(self):
        # 1. Agents Act & Live/Die
        surviving_agents = []
        new_agents = []

        for agent in self.agents:
            agent.move(self.grid)

            # Biological Physics
            current_coherence = agent.coherence

            # Apoptosis (Death from lack of energy or extreme chaos)
            if agent.energy < 10.0:
                # Remove from grid
                section = self.grid.get_sector(agent.x, agent.y)
                if agent in section.agents:
                    section.agents.remove(agent)
                continue  # Agent dies

            # Mitosis (Reproduction from high energy + stability)
            if agent.energy > 150.0 and 0.48 < current_coherence < 0.52:
                # Spawn clone
                child = StabilizerAgent(
                    id=f"{agent.id}_g{agent.generation + 1}_{random.randint(100, 999)}",
                    x=agent.x,
                    y=agent.y,
                    generation=agent.generation + 1,
                    energy=75.0,  # Parent gives energy
                )
                child.z_vector = agent.z_vector.copy() + np.random.normal(
                    0, 0.01, 12
                )  # Slight mutation
                agent.energy -= 75.0

                # Place child
                sector = self.grid.get_sector(child.x, child.y)
                sector.agents.append(child)
                new_agents.append(child)

            surviving_agents.append(agent)

        self.agents = surviving_agents + new_agents

        # 2. Universe Reacts
        self.grid.update_sectors()

        # 3. Log Sample (don't log everything every tick to save space)
        if self.ticks % 10 == 0:
            sample_agent = self.agents[0]
            sector = self.grid.get_sector(sample_agent.x, sample_agent.y)

            self.logger.log_cycle(
                {
                    "cycle_id": f"tick_{self.ticks}",
                    "universe_domain": "fractal_nexus",
                    "sector_type": sector.manifold_type,
                    "spatial_pos": [float(sample_agent.x), float(sample_agent.y)],
                    "energy_level": sample_agent.energy,
                    "phi_score": sample_agent.coherence,
                    "narration": (
                        f"Agent {sample_agent.id} moved to {sector.manifold_type} "
                        f"sector to stabilize entropy."
                    ),
                }
            )

        self.ticks += 1

    def run(self, max_seconds: int = 3600):
        start_time = time.time()
        next_report = start_time + 10

        logger.info(f"Starting Fractal Universe Simulation for {max_seconds} seconds...")

        while self.running and (time.time() - start_time < max_seconds):
            self.step()

            if time.time() > next_report:
                report = f"\nTick {self.ticks} | Stability Map:\n{self.grid.render_ascii()}"
                logger.info(report)
                next_report = time.time() + 60  # Report every minute
                self.logger.flush()

            time.sleep(0.05 / self.monitor.get_dilation_factor())  # Dynamic TPS Dilation


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fractal Universe Simulator")
    parser.add_argument("--duration", type=str, default="3h", help="Duration (e.g. 3h, 30m, 120s)")
    args = parser.parse_args()

    # Parse duration
    units = {"s": 1, "m": 60, "h": 3600}
    unit = args.duration[-1]
    duration_s = int(args.duration[:-1]) * units[unit] if unit in units else int(args.duration)

    sim = FractalSimulator()
    sim.run(max_seconds=duration_s)
