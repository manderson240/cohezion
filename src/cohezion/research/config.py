"""Research agent configuration.

Minimal configuration for autonomous training optimization.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class ResearchConfig:
    """Configuration for research agent.

    Clean, focused config following elegant simplification.
    """

    # Experiment parameters
    experiment_time_budget: float = 300.0  # 5 minutes in seconds
    max_experiments: int = 100  # Per session

    # Training parameters
    model_depth: int = 8
    vocab_size: int = 8192
    max_seq_len: int = 1024
    device_batch_size: int = 16
    total_batch_size: int = 524288  # 2**19

    # Optimization targets
    target_metric: str = "val_bpb"  # validation bits per byte
    metric_direction: str = "minimize"  # lower is better

    # Agent behavior
    temperature: float = 0.7  # For code generation
    max_code_changes: int = 50  # Lines per experiment

    # Paths
    train_file: Path = Path("train.py")
    experiment_log: Path = Path("data/research/experiments.jsonl")
    checkpoint_dir: Path = Path("data/research/checkpoints")

    # Safety
    enable_guardrails: bool = True
    require_human_review: bool = False  # Set True for production

    def __post_init__(self):
        """Ensure directories exist."""
        self.experiment_log.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class ExperimentResult:
    """Result of a single experiment.

    Minimal data class for tracking experiment outcomes.
    """

    experiment_id: str
    timestamp: str
    metric_value: float
    metric_name: str
    improved: bool
    code_changes: list[str]
    duration_seconds: float
    checkpoint_path: Path | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "experiment_id": self.experiment_id,
            "timestamp": self.timestamp,
            "metric_value": self.metric_value,
            "metric_name": self.metric_name,
            "improved": self.improved,
            "code_changes": self.code_changes,
            "duration_seconds": self.duration_seconds,
            "checkpoint_path": str(self.checkpoint_path) if self.checkpoint_path else None,
        }
