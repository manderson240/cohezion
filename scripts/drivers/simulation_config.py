"""
Enhanced Simulation Configuration System
=======================================

YAML-based configuration for all simulation parameters.
Supports environment variable substitution and validation.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SimulationConfig:
    """Base configuration for simulations."""

    # Session settings
    session_id: str | None = None
    archive_dir: str = "/home/mike-anderson/nvme-simulations"
    log_level: str = "INFO"

    # Time limits
    end_time_hour: int = 7  # Stop at 7 AM
    max_duration_hours: float = 8.0

    # Checkpointing
    checkpoint_interval: int = 100_000
    resume_from_checkpoint: str | None = None

    # Parallelization
    max_workers: int = 4
    batch_size: int = 500

    # Persistence
    use_surrealdb: bool = True
    surrealdb_url: str = "ws://localhost:8000/rpc"
    surrealdb_namespace: str = "cohezion"
    surrealdb_database: str = "universe"

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_dashboard: bool = True
    dashboard_port: int = 8080

    # Resource limits
    max_memory_gb: float = 32.0
    max_disk_gb: float = 100.0

    @classmethod
    def from_yaml(cls, path: Path) -> "SimulationConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        # Environment variable substitution
        data = cls._substitute_env_vars(data)

        return cls(**data)

    @classmethod
    def _substitute_env_vars(cls, data: Any) -> Any:
        """Recursively substitute environment variables."""
        if isinstance(data, dict):
            return {k: cls._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            default = None
            if ":" in var_name:
                var_name, default = var_name.split(":", 1)
            return os.getenv(var_name, default)
        return data

    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if self.max_workers < 1:
            issues.append("max_workers must be >= 1")

        if self.batch_size < 1:
            issues.append("batch_size must be >= 1")

        if self.end_time_hour < 0 or self.end_time_hour > 23:
            issues.append("end_time_hour must be between 0 and 23")

        if self.max_memory_gb < 1:
            issues.append("max_memory_gb must be >= 1")

        return issues


@dataclass
class FlumeConfig:
    """Configuration for FLUME simulations."""

    enabled: bool = True
    target_simulations: int = 1000
    streams: list[str] = field(
        default_factory=lambda: [
            "architect",
            "engineer",
            "biologist",
            "quantum_hardware",
            "quantum_algo",
        ]
    )
    use_encoder: bool = False  # Use FLUME VAE if available
    z_dim: int = 256


@dataclass
class RZeroConfig:
    """Configuration for R-Zero simulations."""

    enabled: bool = True
    target_simulations: int = 500_000
    initial_difficulty: float = 1.0
    difficulty_increment: float = 0.05
    success_threshold: float = 0.8
    history_window: int = 20
    edge_cases: list[dict] = field(
        default_factory=lambda: [
            {"name": "Zero Energy Warp", "zpe_limit": 0.1, "warp_target": 2.0},
            {"name": "Infinite Fertility", "fertility_target": 5.0},
            {"name": "Cold Fusion", "temp_limit": 300, "energy_target": 1000},
            {"name": "Standard Op", "zpe_limit": 10.0, "warp_target": 1.0},
        ]
    )


@dataclass
class FractalConfig:
    """Configuration for Fractal Universe simulations."""

    enabled: bool = True
    grid_size: int = 64
    num_agents: int = 10_000
    target_coherence: float = 0.5
    simulation_steps: int = 3600
    agent_energy_decay: float = 0.01
    coherence_learning_rate: float = 0.01


@dataclass
class MassSimConfig:
    """Configuration for Mass Simulation."""

    enabled: bool = True
    target_sweeps: int = 500_000
    parameter_ranges: dict = field(
        default_factory=lambda: {
            "alpha": {"min": 0.1, "max": 2.0},
            "beta": {"min": 0.5, "max": 1.5},
            "gamma": {"min": -1.0, "max": 1.0},
        }
    )


def load_default_config() -> tuple[
    SimulationConfig, FlumeConfig, RZeroConfig, FractalConfig, MassSimConfig
]:
    """Load default configuration for all simulation types."""
    return (
        SimulationConfig(),
        FlumeConfig(),
        RZeroConfig(),
        FractalConfig(),
        MassSimConfig(),
    )


def create_default_config_files(
    config_dir: Path = Path("/home/mike-anderson/nvme-simulations/config"),
) -> None:
    """Create default configuration files."""
    config_dir.mkdir(parents=True, exist_ok=True)

    # Main simulation config
    main_config = SimulationConfig()
    main_config.to_yaml(config_dir / "simulation.yaml")

    # FLUME config
    flume_config = FlumeConfig()
    with open(config_dir / "flume.yaml", "w") as f:
        yaml.dump(flume_config.__dict__, f, default_flow_style=False)

    # R-Zero config
    rzero_config = RZeroConfig()
    with open(config_dir / "rzero.yaml", "w") as f:
        yaml.dump(rzero_config.__dict__, f, default_flow_style=False)

    # Fractal config
    fractal_config = FractalConfig()
    with open(config_dir / "fractal.yaml", "w") as f:
        yaml.dump(fractal_config.__dict__, f, default_flow_style=False)

    # Mass Sim config
    mass_config = MassSimConfig()
    with open(config_dir / "mass.yaml", "w") as f:
        yaml.dump(mass_config.__dict__, f, default_flow_style=False)

    print(f"✅ Configuration files created in {config_dir}")


if __name__ == "__main__":
    create_default_config_files()

    # Test loading
    config = SimulationConfig.from_yaml(
        Path("/home/mike-anderson/nvme-simulations/config/simulation.yaml")
    )
    issues = config.validate()
    if issues:
        print("⚠️  Configuration issues:", issues)
    else:
        print("✅ Configuration valid")
