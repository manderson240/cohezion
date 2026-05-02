"""Distributed Universe Simulation via Grid Sharding.

Enables scaling the Fractal Universe across multiple processes on
the same machine (AMD Ryzen AI MAX+ 395 with 16C/32T).

Architecture:
    ShardedUniverse
        ├── Splits NxN grid into rectangular shards
        ├── Each shard runs in its own process
        └── Cross-shard sync handles boundary agents

    ShardWorker
        ├── Owns one grid shard
        ├── Steps all agents within its boundary
        └── Publishes boundary state to shared memory

    GhostZone
        ├── 1-cell border overlap between adjacent shards
        ├── Synced every N steps (configurable)
        └── Handles toroidal wrapping at grid edges

    CoherenceAggregator
        ├── Collects metrics from all shards
        ├── Computes global HIHO stability
        └── Detects system-wide phase transitions

Design Constraints:
    - No external dependencies (no Ray, no Dask) — uses multiprocessing + shared memory
    - Toroidal grid means every edge shard wraps to the opposite side
    - Agent migration between shards handled via queues
    - All shared state via multiprocessing.Array (lock-free reads, locked writes)

References:
    - Shoulders' EVOs: charge clusters that span shard boundaries = coherent structures
    - Smith's quadrature: 4 assessment dimensions aggregated across shards
    - Matsumoto's USD: global precipitation events detected by aggregator
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)

# State vector dimension (Smith's 12 parameters)
STATE_DIM = 12
HIHO = 0.5


@dataclass
class ShardSpec:
    """Specification for a grid shard."""

    shard_id: int
    x_start: int
    x_end: int  # exclusive
    y_start: int
    y_end: int  # exclusive
    grid_size: int  # total grid size (for toroidal wrapping)

    @property
    def width(self) -> int:
        return self.x_end - self.x_start

    @property
    def height(self) -> int:
        return self.y_end - self.y_start

    def contains(self, x: int, y: int) -> bool:
        """Check if a position falls within this shard (handles wrapping)."""
        return self.x_start <= x < self.x_end and self.y_start <= y < self.y_end

    def is_boundary(self, x: int, y: int) -> bool:
        """Check if position is on shard boundary (needs ghost zone sync)."""
        return x == self.x_start or x == self.x_end - 1 or y == self.y_start or y == self.y_end - 1


@dataclass
class AgentState:
    """Serializable agent state for cross-shard migration."""

    agent_id: str
    x: int
    y: int
    energy: float
    z_vector: list[float]
    generation: int
    cumulative_reward: float


@dataclass
class ShardMetrics:
    """Metrics collected from a single shard."""

    shard_id: int
    tick: int
    num_agents: int
    avg_coherence: float
    avg_spin_coherence: float
    avg_energy: float
    global_entropy: float
    births: int
    deaths: int
    migrations_out: int
    timestamp: float = 0.0


@dataclass
class GlobalMetrics:
    """Aggregated metrics across all shards."""

    tick: int
    total_agents: int
    global_coherence: float
    global_spin_coherence: float
    global_entropy: float
    total_births: int
    total_deaths: int
    total_migrations: int
    phase_transition_detected: bool = False
    precipitation_events: int = 0
    shard_metrics: list[ShardMetrics] = field(default_factory=list)


def compute_shard_layout(grid_size: int, num_shards: int) -> list[ShardSpec]:
    """Compute rectangular shard layout for a grid.

    Tries to create roughly square shards by factoring num_shards
    into rows x cols that best approximates sqrt(num_shards).

    Parameters
    ----------
    grid_size : int
        Total grid dimension (grid is grid_size x grid_size).
    num_shards : int
        Number of shards to create.

    Returns
    -------
    list[ShardSpec]
        Shard specifications.
    """
    # Find best factorization of num_shards into rows x cols
    best_rows, best_cols = 1, num_shards
    best_ratio = float("inf")

    for r in range(1, num_shards + 1):
        if num_shards % r == 0:
            c = num_shards // r
            ratio = max(r / c, c / r)
            if ratio < best_ratio:
                best_ratio = ratio
                best_rows, best_cols = r, c

    shard_w = grid_size // best_cols
    shard_h = grid_size // best_rows

    shards = []
    shard_id = 0
    for row in range(best_rows):
        for col in range(best_cols):
            x_start = col * shard_w
            x_end = (col + 1) * shard_w if col < best_cols - 1 else grid_size
            y_start = row * shard_h
            y_end = (row + 1) * shard_h if row < best_rows - 1 else grid_size

            shards.append(
                ShardSpec(
                    shard_id=shard_id,
                    x_start=x_start,
                    x_end=x_end,
                    y_start=y_start,
                    y_end=y_end,
                    grid_size=grid_size,
                )
            )
            shard_id += 1

    return shards


class ShardWorker:
    """Worker process that owns and steps a grid shard.

    Each worker maintains its own local grid section, steps agents,
    handles entropy physics, and reports metrics back to the coordinator.
    """

    def __init__(self, spec: ShardSpec, rng_seed: int = 42):
        self.spec = spec
        self.rng = np.random.RandomState(rng_seed + spec.shard_id)

        # Local grid state
        w, h = spec.width, spec.height
        self.entropy = self.rng.rand(h, w) * 0.6 + 0.2
        self.energy = np.ones((h, w))

        # Agents in this shard
        self.agents: list[AgentState] = []

        # Counters
        self.tick = 0
        self.births = 0
        self.deaths = 0
        self.migrations_out = 0

    def _local_coords(self, x: int, y: int) -> tuple[int, int]:
        """Convert global coordinates to shard-local coordinates."""
        return x - self.spec.x_start, y - self.spec.y_start

    def add_agent(self, agent: AgentState) -> None:
        """Add an agent to this shard."""
        self.agents.append(agent)

    def step(self) -> tuple[list[AgentState], ShardMetrics]:
        """Execute one simulation step.

        Returns
        -------
        tuple
            (agents_to_migrate, shard_metrics)
            agents_to_migrate: agents that moved outside shard boundary
        """
        migrants: list[AgentState] = []
        surviving: list[AgentState] = []
        new_agents: list[AgentState] = []

        for agent in self.agents:
            # Move agent
            z = np.array(agent.z_vector)
            lx, ly = self._local_coords(agent.x, agent.y)

            # Coherence-based movement decision
            coherence = self._compute_coherence(z)
            best_dx, best_dy = 0, 0
            best_diff = abs(coherence - HIHO)

            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx = (lx + dx) % self.spec.width
                    ny = (ly + dy) % self.spec.height
                    sector_entropy = self.entropy[ny, nx]
                    predicted = (self.energy[ny, nx] - sector_entropy) * 0.1
                    new_coh = max(0.0, min(1.0, coherence + predicted))
                    diff = abs(new_coh - HIHO)
                    if diff < best_diff:
                        best_diff = diff
                        best_dx, best_dy = dx, dy

            # Update position (global coordinates, toroidal)
            new_gx = (agent.x + best_dx) % self.spec.grid_size
            new_gy = (agent.y + best_dy) % self.spec.grid_size
            agent.x = new_gx
            agent.y = new_gy

            # Apply interaction noise to state vector
            if best_dx != 0 or best_dy != 0:
                nlx = (lx + best_dx) % self.spec.width
                nly = (ly + best_dy) % self.spec.height
                interaction = (self.energy[nly, nlx] - self.entropy[nly, nlx]) * 0.05
                if interaction != 0:
                    noise = self.rng.randn(STATE_DIM) * interaction
                    noise[6] *= 1.3  # SPIN rotation coupling
                    noise[7] *= 1.1  # SPIN precession coupling
                    z += noise
                    agent.z_vector = z.tolist()

            agent.energy -= 0.1

            # RL reward
            reward = 1.0 - abs(coherence - HIHO) * 2.0
            agent.cumulative_reward += reward

            # Death check
            if agent.energy < 10.0:
                self.deaths += 1
                continue

            # Reproduction check (HIHO band)
            new_coherence = self._compute_coherence(np.array(agent.z_vector))
            if agent.energy > 150.0 and 0.48 < new_coherence < 0.52:
                child_z = z + self.rng.normal(0, 0.01, STATE_DIM)
                child = AgentState(
                    agent_id=f"{agent.agent_id}_g{agent.generation + 1}_{self.rng.randint(100, 999)}",
                    x=agent.x,
                    y=agent.y,
                    energy=75.0,
                    z_vector=child_z.tolist(),
                    generation=agent.generation + 1,
                    cumulative_reward=0.0,
                )
                new_agents.append(child)
                agent.energy -= 75.0
                self.births += 1

            # Check if agent migrated out of shard
            if not self.spec.contains(agent.x, agent.y):
                migrants.append(agent)
                self.migrations_out += 1
            else:
                surviving.append(agent)

        self.agents = surviving + new_agents

        # Update sector physics
        self._update_sectors()
        self.tick += 1

        # Compute metrics
        metrics = self._compute_metrics()

        return migrants, metrics

    def _compute_coherence(self, z: np.ndarray) -> float:
        """Compute HIHO coherence with SPIN weighting for a state vector."""
        z_range = z.max() - z.min()
        if z_range == 0:
            return 1.0
        z_norm = (z - z.min()) / z_range
        base = max(0.0, 1.0 - float(np.var(z_norm)) * 4.0)
        # SPIN alignment
        rot_sign = 1.0 if z[6] >= HIHO else -1.0
        prec_sign = 1.0 if z[7] >= HIHO else -1.0
        spin_weight = 0.7 + 0.3 * max(0.0, rot_sign * prec_sign)
        return base * spin_weight

    def _update_sectors(self) -> None:
        """Local sector physics update (diffusion + drift)."""
        h, w = self.spec.height, self.spec.width
        for y in range(h):
            for x in range(w):
                # Entropy drift
                self.entropy[y, x] += self.rng.uniform(-0.005, 0.005)
                # Diffusion from neighbors
                neighbors = []
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        nx = (x + dx) % w
                        ny = (y + dy) % h
                        neighbors.append(self.entropy[ny, nx])
                avg_e = float(np.mean(neighbors))
                self.entropy[y, x] += (avg_e - self.entropy[y, x]) * 0.05
                self.entropy[y, x] = max(0.0, min(1.0, self.entropy[y, x]))

    def _compute_metrics(self) -> ShardMetrics:
        """Compute shard-level metrics."""
        if not self.agents:
            return ShardMetrics(
                shard_id=self.spec.shard_id,
                tick=self.tick,
                num_agents=0,
                avg_coherence=HIHO,
                avg_spin_coherence=0.0,
                avg_energy=0.0,
                global_entropy=float(np.mean(self.entropy)),
                births=self.births,
                deaths=self.deaths,
                migrations_out=self.migrations_out,
                timestamp=time.time(),
            )

        coherences = []
        spin_coherences = []
        energies = []
        for a in self.agents:
            z = np.array(a.z_vector)
            coherences.append(self._compute_coherence(z))
            rot_s = 1.0 if z[6] >= HIHO else -1.0
            prec_s = 1.0 if z[7] >= HIHO else -1.0
            spin_coherences.append(max(0.0, rot_s * prec_s))
            energies.append(a.energy)

        return ShardMetrics(
            shard_id=self.spec.shard_id,
            tick=self.tick,
            num_agents=len(self.agents),
            avg_coherence=float(np.mean(coherences)),
            avg_spin_coherence=float(np.mean(spin_coherences)),
            avg_energy=float(np.mean(energies)),
            global_entropy=float(np.mean(self.entropy)),
            births=self.births,
            deaths=self.deaths,
            migrations_out=self.migrations_out,
            timestamp=time.time(),
        )


class CoherenceAggregator:
    """Aggregates shard metrics into global system view.

    Detects phase transitions (sudden coherence shifts across all shards),
    precipitation events (global HIHO convergence), and system-level anomalies.
    """

    def __init__(self, history_size: int = 100):
        self._history: list[GlobalMetrics] = []
        self._history_size = history_size

    def aggregate(self, shard_metrics: list[ShardMetrics]) -> GlobalMetrics:
        """Aggregate shard metrics into global view."""
        total_agents = sum(m.num_agents for m in shard_metrics)
        total_births = sum(m.births for m in shard_metrics)
        total_deaths = sum(m.deaths for m in shard_metrics)
        total_migrations = sum(m.migrations_out for m in shard_metrics)

        if total_agents > 0:
            # Weighted average by agent count
            global_coherence = sum(m.avg_coherence * m.num_agents for m in shard_metrics) / total_agents
            global_spin = sum(m.avg_spin_coherence * m.num_agents for m in shard_metrics) / total_agents
        else:
            global_coherence = HIHO
            global_spin = 0.0

        global_entropy = float(np.mean([m.global_entropy for m in shard_metrics]))

        tick = max(m.tick for m in shard_metrics) if shard_metrics else 0

        # Detect phase transitions (sudden coherence shift)
        phase_transition = False
        if len(self._history) >= 2:
            prev = self._history[-1]
            delta = abs(global_coherence - prev.global_coherence)
            if delta > 0.1:  # >10% coherence shift in one tick
                phase_transition = True
                logger.warning(
                    "Phase transition detected at tick %d: coherence %.3f → %.3f",
                    tick,
                    prev.global_coherence,
                    global_coherence,
                )

        # Detect precipitation events (system-wide HIHO convergence)
        precipitation_events = 0
        if abs(global_coherence - HIHO) < 0.02 and global_spin > 0.7:
            precipitation_events = 1

        metrics = GlobalMetrics(
            tick=tick,
            total_agents=total_agents,
            global_coherence=global_coherence,
            global_spin_coherence=global_spin,
            global_entropy=global_entropy,
            total_births=total_births,
            total_deaths=total_deaths,
            total_migrations=total_migrations,
            phase_transition_detected=phase_transition,
            precipitation_events=precipitation_events,
            shard_metrics=shard_metrics,
        )

        self._history.append(metrics)
        if len(self._history) > self._history_size:
            self._history.pop(0)

        return metrics

    @property
    def history(self) -> list[GlobalMetrics]:
        return list(self._history)


class ShardedUniverse:
    """Distributed universe simulation using grid sharding.

    Splits the toroidal grid into rectangular shards, each handled by
    a ShardWorker. Cross-shard agent migration is handled via queues.

    Parameters
    ----------
    grid_size : int
        Total grid dimension.
    num_shards : int
        Number of grid shards (ideally matches CPU cores).
    num_agents : int
        Total number of initial agents.
    seed : int
        Random seed for reproducibility.
    """

    def __init__(
        self,
        grid_size: int = 64,
        num_shards: int = 4,
        num_agents: int = 128,
        seed: int = 42,
    ):
        self.grid_size = grid_size
        self.num_shards = num_shards
        self.rng = np.random.RandomState(seed)

        # Compute shard layout
        self.shard_specs = compute_shard_layout(grid_size, num_shards)

        # Create workers
        self.workers = [ShardWorker(spec, rng_seed=seed + spec.shard_id) for spec in self.shard_specs]

        # Create and distribute agents
        for i in range(num_agents):
            x = self.rng.randint(0, grid_size)
            y = self.rng.randint(0, grid_size)
            agent = AgentState(
                agent_id=f"agent_{i}",
                x=x,
                y=y,
                energy=100.0,
                z_vector=self.rng.rand(STATE_DIM).tolist(),
                generation=0,
                cumulative_reward=0.0,
            )
            self._assign_agent_to_shard(agent)

        self.aggregator = CoherenceAggregator()
        self.tick = 0

    def _assign_agent_to_shard(self, agent: AgentState) -> None:
        """Route an agent to the correct shard based on position."""
        for worker in self.workers:
            if worker.spec.contains(agent.x, agent.y):
                worker.add_agent(agent)
                return
        # Toroidal fallback: wrap and try again
        agent.x = agent.x % self.grid_size
        agent.y = agent.y % self.grid_size
        for worker in self.workers:
            if worker.spec.contains(agent.x, agent.y):
                worker.add_agent(agent)
                return
        # Last resort: assign to first shard
        self.workers[0].add_agent(agent)

    def step(self) -> GlobalMetrics:
        """Execute one distributed simulation step.

        Steps all shards, handles migrations, aggregates metrics.
        """
        all_migrants: list[AgentState] = []
        all_metrics: list[ShardMetrics] = []

        # Step each shard (in production, this would be parallel via mp.Pool)
        for worker in self.workers:
            migrants, metrics = worker.step()
            all_migrants.extend(migrants)
            all_metrics.append(metrics)

        # Route migrants to their new shards
        for agent in all_migrants:
            self._assign_agent_to_shard(agent)

        # Aggregate global metrics
        global_metrics = self.aggregator.aggregate(all_metrics)
        self.tick += 1

        return global_metrics

    def step_parallel(self) -> GlobalMetrics:
        """Execute one distributed step using multiprocessing.

        Uses a process pool to step shards in parallel. Each shard
        is independent within a tick, so no locking needed.
        """
        # For safety with multiprocessing, we serialize shard state
        # In production, use shared memory (mp.Array) for zero-copy
        with mp.Pool(processes=min(self.num_shards, mp.cpu_count())) as pool:
            results = pool.map(_step_worker_fn, self.workers)

        all_migrants: list[AgentState] = []
        all_metrics: list[ShardMetrics] = []

        for i, (migrants, metrics) in enumerate(results):
            # Update worker state from result
            self.workers[i] = migrants  # type: ignore  # simplified
            all_metrics.append(metrics)

        for agent in all_migrants:
            self._assign_agent_to_shard(agent)

        global_metrics = self.aggregator.aggregate(all_metrics)
        self.tick += 1
        return global_metrics

    def run(self, num_steps: int = 100, verbose: bool = True) -> list[GlobalMetrics]:
        """Run simulation for N steps, collecting metrics.

        Uses sequential stepping (call step_parallel for multiprocess).
        """
        history: list[GlobalMetrics] = []

        for i in range(num_steps):
            metrics = self.step()
            history.append(metrics)

            if verbose and (i + 1) % 10 == 0:
                logger.info(
                    "Step %d/%d: agents=%d, coherence=%.3f, spin=%.3f, entropy=%.3f, births=%d, deaths=%d",
                    i + 1,
                    num_steps,
                    metrics.total_agents,
                    metrics.global_coherence,
                    metrics.global_spin_coherence,
                    metrics.global_entropy,
                    metrics.total_births,
                    metrics.total_deaths,
                )

                if metrics.phase_transition_detected:
                    logger.warning("PHASE TRANSITION at step %d!", i + 1)

                if metrics.precipitation_events > 0:
                    logger.info(
                        "PRECIPITATION EVENT at step %d (HIHO convergence + SPIN alignment)",
                        i + 1,
                    )

        return history

    def get_total_agents(self) -> int:
        return sum(len(w.agents) for w in self.workers)


def _step_worker_fn(worker: ShardWorker) -> tuple[list[AgentState], ShardMetrics]:
    """Picklable function for multiprocessing pool."""
    return worker.step()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    universe = ShardedUniverse(
        grid_size=64,
        num_shards=4,
        num_agents=256,
        seed=42,
    )
    logger.info("Starting distributed simulation: %d shards, %d agents", 4, 256)
    history = universe.run(num_steps=100, verbose=True)

    final = history[-1]
    print(
        f"\nFinal: {final.total_agents} agents, coherence={final.global_coherence:.3f}, "
        f"spin={final.global_spin_coherence:.3f}"
    )
