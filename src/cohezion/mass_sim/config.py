# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Configuration for mass simulation runs.

Defines scale tiers, universe specs, and simulation parameters with
OOM-safe defaults tuned for AMD Ryzen AI MAX+ 395 (128GB unified).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ScaleTier:
    """Defines simulation scale parameters."""

    name: str
    n_agents: int
    n_epochs: int
    n_universes: int
    checkpoint_interval: int  # Save state every N epochs
    batch_size: int  # Agents per Rust batch call (memory-bounded)


# Pre-defined scale tiers tuned for Strix Halo (128GB unified RAM)
# Memory budget per batch: batch_size * z_dim * 4 bytes
# e.g. 10_000 * 256 * 4 = 10MB per batch (safe)
SCALE_TIERS: dict[str, ScaleTier] = {
    "demo": ScaleTier("demo", 100, 1_000, 10, 100, 100),
    "medium": ScaleTier("medium", 1_000, 10_000, 100, 1_000, 500),
    "overnight": ScaleTier("overnight", 10_000, 100_000, 1_000, 5_000, 2_000),
    "aspirational": ScaleTier("aspirational", 25_000_000, 10_000_000, 1_000_000, 100_000, 10_000),
}


@dataclass
class UniverseSpec:
    """Specification for a single universe (unique weight configuration)."""

    universe_id: str
    seed: int
    z_dim: int = 256
    hidden_dim: int = 512


@dataclass
class CheckpointData:
    """Snapshot at a simulation checkpoint."""

    epoch: int
    stats: dict  # From FlumePhysics.compute_batch_stats
    sample_states: list | None = None  # First N agents for visualization


@dataclass
class UniverseResult:
    """Complete results from simulating one universe."""

    universe_id: str
    seed: int
    n_agents: int
    n_epochs: int
    initial_stats: dict
    final_stats: dict
    checkpoints: list[CheckpointData] = field(default_factory=list)
    elapsed_seconds: float = 0.0


@dataclass
class SimulationReport:
    """Aggregated results across all universes."""

    run_id: str
    config_name: str
    n_universes: int
    n_agents: int
    n_epochs: int
    universe_results: list[UniverseResult] = field(default_factory=list)
    insights: dict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    total_elapsed_seconds: float = 0.0

    def summary_dict(self) -> dict:
        """Compact summary for logging."""
        return {
            "run_id": self.run_id,
            "scale": self.config_name,
            "universes": self.n_universes,
            "agents_per_universe": self.n_agents,
            "epochs": self.n_epochs,
            "total_agent_epochs": self.n_universes * self.n_agents * self.n_epochs,
            "elapsed_seconds": round(self.total_elapsed_seconds, 2),
            "insights": self.insights,
            "artifacts_generated": len(self.artifacts),
        }


@dataclass
class SimulationConfig:
    """Full configuration for a mass simulation run."""

    scale: ScaleTier
    use_navigator: bool = True
    coherence_bounds: tuple[float, float] = (0.3, 0.7)
    persist_to_db: bool = True
    artifact_dir: Path = Path("data/mass_sim/artifacts")
    checkpoint_dir: Path = Path("data/mass_sim/checkpoints")
    agent_seed_base: int = 42
    universe_seeds: list[int] | None = None
    # OOM protection: max RSS in GB before pausing
    max_memory_gb: float = 100.0
    # Sample agents to store per checkpoint (full state)
    checkpoint_sample_size: int = 10
    # Navigator delta scaling (multiplied into state update per epoch)
    delta_scale: float = 0.01
    # HIHO damping factor (attractor strength toward 0.5 equilibrium)
    # 0.05 provides 5% pull toward 0.5 per step — balances convergence within HIHO bounds with diversity preservation
    hiho_damping: float = 0.05
    # Export final agent states as .npy files for training pipeline
    export_npy: bool = False

    def with_overrides(
        self,
        agents: int | None = None,
        epochs: int | None = None,
        universes: int | None = None,
    ) -> SimulationConfig:
        """Create new config with CLI overrides applied."""
        tier = self.scale
        if agents is not None:
            tier = dataclasses.replace(tier, n_agents=agents)
        if epochs is not None:
            tier = dataclasses.replace(tier, n_epochs=epochs)
        if universes is not None:
            tier = dataclasses.replace(tier, n_universes=universes)
        return dataclasses.replace(self, scale=tier)
