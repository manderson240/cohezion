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

from cohezion.cosmic.reality import get_reality_stabilizer
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
    )  # 12D State Vector
    memory: list[dict] = field(default_factory=list)
    generation: int = 0
    learning_rate: float = 0.1

    @property
    def coherence(self) -> float:
        # Use RealityStabilizer
        stabilizer = get_reality_stabilizer()
        return stabilizer.calculate_stability(self.z_vector)

    def move(self, grid: "UniverseGrid"):
        neighbors = grid.get_neighbors(self.x, self.y)

        best_move = None
        min_diff = abs(self.coherence - 0.5)

        # Stabilizer access omitted for independent simulation logic
        # Using self.coherence property

        for nx, ny, sector in neighbors:
            # Predict effect of moving to this sector
            # Physics: Interaction depends on local energy gradient and entropy
            predicted_change = (sector.energy - sector.entropy) * 0.1
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

            # Apply feedback interaction (Reality Physics)
            interaction = (new_sector.energy - new_sector.entropy) * 0.05
            old_coherence = self.coherence

            # Update internal Vector or Coherence?
            # The Proposal calls for direct coherence update, but class has z_vector property.
            # We will abstract the vector update to match the coherence shift.
            # Simplified: Adjust vector magnitude or noise to shift coherence.
            if interaction != 0:
                # Add scaled noise to shift state
                noise = np.random.randn(12) * interaction
                self.z_vector += noise

            # Store memory of action and outcome
            self.memory.append(
                {
                    "position": (self.x, self.y),
                    "prev_coherence": old_coherence,
                    "new_coherence": self.coherence,
                    "sector_type": new_sector.manifold_type,
                    "energy": new_sector.energy,
                    "entropy": new_sector.entropy,
                }
            )

            # Adaptive learning (Memory Buffer limit)
            if len(self.memory) > 10:
                self.memory.pop(0)

            self.energy -= 0.1  # Movement cost


class UniverseGrid:
    def __init__(self, size: int = GRID_SIZE):
        self.size = size
        self.grid = [
            [Sector(x, y, random.choice(SECTOR_TYPES)) for x in range(size)]
            for y in range(size)
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
                (avg_entropy - sector.entropy) * 0.05

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

        # Update grid in place (simplification, strictly should be new grid object but refs complicate it)
        # Since we modified sector objects directly above, we don't strictly need to reassign,
        # but the diffusion step used current values.
        # For a truthful CA we should use a buffer, but for this simulation direct update is 'chaotic' enough.
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
                    id=f"{agent.id}_g{agent.generation+1}_{random.randint(100,999)}",
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
                    "narration": f"Agent {sample_agent.id} moved to {sector.manifold_type} sector to stabilize entropy.",
                }
            )

        self.ticks += 1

    def run(self, max_seconds: int = 3600):
        start_time = time.time()
        next_report = start_time + 10

        logger.info(
            f"Starting Fractal Universe Simulation for {max_seconds} seconds..."
        )

        while self.running and (time.time() - start_time < max_seconds):
            self.step()

            if time.time() > next_report:
                report = (
                    f"\nTick {self.ticks} | Stability Map:\n{self.grid.render_ascii()}"
                )
                logger.info(report)
                next_report = time.time() + 60  # Report every minute
                self.logger.flush()

            time.sleep(
                0.05 / self.monitor.get_dilation_factor()
            )  # Dynamic TPS Dilation


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fractal Universe Simulator")
    parser.add_argument(
        "--duration", type=str, default="3h", help="Duration (e.g. 3h, 30m, 120s)"
    )
    args = parser.parse_args()

    # Parse duration
    units = {"s": 1, "m": 60, "h": 3600}
    unit = args.duration[-1]
    if unit in units:
        duration_s = int(args.duration[:-1]) * units[unit]
    else:
        duration_s = int(args.duration)

    sim = FractalSimulator()
    sim.run(max_seconds=duration_s)
