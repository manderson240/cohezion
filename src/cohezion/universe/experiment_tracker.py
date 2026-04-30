"""Experiment Tracker for Reproducible Universe Simulations.

Provides deterministic experiment management: seed tracking, configuration
snapshots, metric logging, checkpoint management, and run comparison.

This is essential ML infrastructure for the Universes team workflow:
- Every simulation run has a unique ID, pinned seed, and frozen config
- Metrics are logged at each step (coherence, reward, loss, etc.)
- Runs can be compared across configurations and model versions
- Checkpoints enable resume-from-failure and replay

Architecture:
    ExperimentTracker (singleton)
        ├── create_run(): Initialize a tracked experiment run
        ├── log_metric(): Record a metric at a given step
        ├── log_config(): Snapshot run configuration
        ├── save_checkpoint(): Persist model/env state
        └── compare_runs(): Statistical comparison of two runs

    ExperimentRun
        ├── Unique run_id, seed, config snapshot
        ├── Metric time series (step → {metric_name: value})
        ├── Checkpoint references
        └── Status tracking (running, completed, failed)

    RunComparison
        ├── Statistical tests across metrics
        ├── Visualization-ready output
        └── Regression detection integration

Storage:
    - Runs stored as JSONL in data/experiments/{run_id}/
    - Checkpoints stored as .npz in data/experiments/{run_id}/checkpoints/
    - Index file at data/experiments/index.jsonl for fast lookup

References:
    - MLflow / Weights & Biases patterns (simplified, no external deps)
    - Cohezion's JourneyTracker for artifact registration
    - Smith's HIHO: coherence trajectory as a first-class metric
"""

from __future__ import annotations

import hashlib
import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class RunStatus(StrEnum):
    """Experiment run status."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass
class MetricEntry:
    """A single metric measurement."""

    step: int
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class CheckpointRef:
    """Reference to a saved checkpoint."""

    checkpoint_id: str
    step: int
    path: str
    size_bytes: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunConfig:
    """Frozen configuration snapshot for a run."""

    seed: int
    environment: dict[str, Any]
    agent: dict[str, Any]
    training: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def config_hash(self) -> str:
        """Deterministic hash of config for deduplication."""
        content = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ExperimentRun:
    """A tracked experiment run.

    Parameters
    ----------
    run_id : str
        Unique run identifier.
    name : str
        Human-readable run name.
    config : RunConfig
        Frozen configuration.
    status : RunStatus
        Current run status.
    """

    run_id: str
    name: str
    config: RunConfig
    status: RunStatus = RunStatus.CREATED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    metrics: dict[str, list[MetricEntry]] = field(default_factory=dict)
    checkpoints: list[CheckpointRef] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    @property
    def duration_seconds(self) -> float | None:
        """Run duration if completed."""
        if self.completed_at is None:
            return None
        start = datetime.fromisoformat(self.created_at)
        end = datetime.fromisoformat(self.completed_at)
        return (end - start).total_seconds()

    def get_metric_series(self, name: str) -> list[tuple[int, float]]:
        """Get (step, value) series for a metric."""
        entries = self.metrics.get(name, [])
        return [(e.step, e.value) for e in entries]

    def get_final_metrics(self) -> dict[str, float]:
        """Get the last recorded value for each metric."""
        finals: dict[str, float] = {}
        for name, entries in self.metrics.items():
            if entries:
                finals[name] = entries[-1].value
        return finals

    def summary(self) -> dict[str, Any]:
        """Generate run summary."""
        return {
            "run_id": self.run_id,
            "name": self.name,
            "status": self.status.value,
            "seed": self.config.seed,
            "config_hash": self.config.config_hash,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration": self.duration_seconds,
            "num_metrics": sum(len(v) for v in self.metrics.values()),
            "num_checkpoints": len(self.checkpoints),
            "final_metrics": self.get_final_metrics(),
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# Run comparison
# ---------------------------------------------------------------------------


@dataclass
class MetricComparison:
    """Statistical comparison of a metric across two runs."""

    metric_name: str
    run_a_mean: float
    run_b_mean: float
    run_a_std: float
    run_b_std: float
    delta: float
    delta_percent: float
    significant: bool
    p_value: float | None = None


@dataclass
class RunComparison:
    """Complete comparison between two experiment runs."""

    run_a_id: str
    run_b_id: str
    metric_comparisons: list[MetricComparison]
    common_metrics: list[str]
    summary: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Experiment tracker
# ---------------------------------------------------------------------------


class ExperimentTracker:
    """Central experiment tracking system.

    Manages experiment runs, metric logging, checkpoint persistence,
    and cross-run comparison. All data persists to local filesystem
    (no external service dependencies).

    Parameters
    ----------
    base_dir : str | Path
        Root directory for experiment data.
    """

    _instance: ExperimentTracker | None = None

    def __init__(self, base_dir: str | Path = "data/experiments"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._runs: dict[str, ExperimentRun] = {}
        self._active_run: ExperimentRun | None = None
        self._index_path = self.base_dir / "index.jsonl"

        # Load existing index
        self._load_index()

    @classmethod
    def get_instance(cls, base_dir: str | Path = "data/experiments") -> ExperimentTracker:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(base_dir)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def create_run(
        self,
        name: str,
        config: RunConfig,
        tags: dict[str, str] | None = None,
        notes: str = "",
    ) -> ExperimentRun:
        """Create and register a new experiment run.

        Parameters
        ----------
        name : str
            Human-readable name.
        config : RunConfig
            Frozen configuration snapshot.
        tags : dict, optional
            Searchable tags.
        notes : str
            Free-text notes.

        Returns
        -------
        ExperimentRun
            The created run.
        """
        run_id = f"run_{uuid4().hex[:8]}"
        run = ExperimentRun(
            run_id=run_id,
            name=name,
            config=config,
            tags=tags or {},
            notes=notes,
        )

        # Set seed for reproducibility
        np.random.seed(config.seed)

        self._runs[run_id] = run
        self._active_run = run

        # Create run directory
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "checkpoints").mkdir(exist_ok=True)

        # Save config
        config_path = run_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(asdict(config), f, indent=2)

        # Update index
        self._append_to_index(run)

        logger.info(
            "Created experiment run: %s (%s), seed=%d, config=%s",
            run_id,
            name,
            config.seed,
            config.config_hash,
        )

        return run

    def start_run(self, run_id: str | None = None) -> ExperimentRun:
        """Mark a run as running.

        Parameters
        ----------
        run_id : str, optional
            Run to start. If None, uses active run.

        Returns
        -------
        ExperimentRun
            The started run.
        """
        run = self._resolve_run(run_id)
        run.status = RunStatus.RUNNING
        self._active_run = run
        return run

    def end_run(
        self,
        run_id: str | None = None,
        status: RunStatus = RunStatus.COMPLETED,
    ) -> ExperimentRun:
        """Mark a run as completed or failed.

        Parameters
        ----------
        run_id : str, optional
            Run to end. If None, uses active run.
        status : RunStatus
            Final status.

        Returns
        -------
        ExperimentRun
            The ended run.
        """
        run = self._resolve_run(run_id)
        run.status = status
        run.completed_at = datetime.now().isoformat()

        # Save final metrics
        self._save_run_data(run)

        if self._active_run and self._active_run.run_id == run.run_id:
            self._active_run = None

        logger.info(
            "Ended run %s: status=%s, duration=%.1fs",
            run.run_id,
            status.value,
            run.duration_seconds or 0.0,
        )

        return run

    def log_metric(
        self,
        name: str,
        value: float,
        step: int,
        run_id: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Log a metric value at a given step.

        Parameters
        ----------
        name : str
            Metric name (e.g., "coherence", "reward", "loss").
        value : float
            Metric value.
        step : int
            Training/simulation step.
        run_id : str, optional
            Run to log to. If None, uses active run.
        tags : dict, optional
            Additional tags for this measurement.
        """
        run = self._resolve_run(run_id)
        entry = MetricEntry(step=step, name=name, value=value, tags=tags or {})

        if name not in run.metrics:
            run.metrics[name] = []
        run.metrics[name].append(entry)

    def log_metrics(
        self,
        metrics: dict[str, float],
        step: int,
        run_id: str | None = None,
    ) -> None:
        """Log multiple metrics at once.

        Parameters
        ----------
        metrics : dict
            Metric name → value pairs.
        step : int
            Training/simulation step.
        run_id : str, optional
            Run to log to.
        """
        for name, value in metrics.items():
            self.log_metric(name, value, step, run_id)

    def save_checkpoint(
        self,
        state: dict[str, Any],
        step: int,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CheckpointRef:
        """Save a checkpoint (model weights, env state, etc.).

        Parameters
        ----------
        state : dict
            State to save. Values should be numpy arrays or serializable.
        step : int
            Step number for this checkpoint.
        run_id : str, optional
            Run to save checkpoint for.
        metadata : dict, optional
            Additional checkpoint metadata.

        Returns
        -------
        CheckpointRef
            Reference to the saved checkpoint.
        """
        run = self._resolve_run(run_id)
        checkpoint_id = f"ckpt_{step:06d}"

        run_dir = self.base_dir / run.run_id / "checkpoints"
        checkpoint_path = run_dir / f"{checkpoint_id}.npz"

        # Separate numpy arrays from other data
        np_arrays = {}
        other_data = {}
        for key, val in state.items():
            if isinstance(val, np.ndarray):
                np_arrays[key] = val
            else:
                other_data[key] = val

        # Save numpy arrays
        if np_arrays:
            np.savez_compressed(checkpoint_path, **np_arrays)

        # Save other data as JSON sidecar
        if other_data:
            sidecar_path = run_dir / f"{checkpoint_id}_meta.json"
            with open(sidecar_path, "w") as f:
                json.dump(other_data, f, indent=2, default=str)

        size = checkpoint_path.stat().st_size if checkpoint_path.exists() else 0

        ref = CheckpointRef(
            checkpoint_id=checkpoint_id,
            step=step,
            path=str(checkpoint_path),
            size_bytes=size,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        run.checkpoints.append(ref)

        logger.debug("Saved checkpoint %s at step %d (%d bytes)", checkpoint_id, step, size)
        return ref

    def load_checkpoint(
        self,
        run_id: str,
        step: int | None = None,
    ) -> dict[str, Any]:
        """Load a checkpoint.

        Parameters
        ----------
        run_id : str
            Run to load from.
        step : int, optional
            Step to load. If None, loads latest.

        Returns
        -------
        dict
            Loaded state.
        """
        run = self._runs.get(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        if not run.checkpoints:
            raise ValueError(f"No checkpoints for run: {run_id}")

        if step is not None:
            ref = next((c for c in run.checkpoints if c.step == step), None)
            if ref is None:
                raise ValueError(f"No checkpoint at step {step} for run {run_id}")
        else:
            ref = run.checkpoints[-1]  # Latest

        state: dict[str, Any] = {}

        # Load numpy arrays
        checkpoint_path = Path(ref.path)
        if checkpoint_path.exists():
            loaded = np.load(checkpoint_path)
            for key in loaded.files:
                state[key] = loaded[key]

        # Load JSON sidecar
        sidecar_path = checkpoint_path.parent / f"{ref.checkpoint_id}_meta.json"
        if sidecar_path.exists():
            with open(sidecar_path) as f:
                state.update(json.load(f))

        return state

    def compare_runs(
        self,
        run_a_id: str,
        run_b_id: str,
    ) -> RunComparison:
        """Compare two experiment runs statistically.

        Parameters
        ----------
        run_a_id : str
            First run ID.
        run_b_id : str
            Second run ID.

        Returns
        -------
        RunComparison
            Statistical comparison.
        """
        run_a = self._runs.get(run_a_id)
        run_b = self._runs.get(run_b_id)

        if not run_a or not run_b:
            raise ValueError("One or both runs not found")

        common_metrics = set(run_a.metrics.keys()) & set(run_b.metrics.keys())
        comparisons: list[MetricComparison] = []

        for metric_name in sorted(common_metrics):
            a_values = [e.value for e in run_a.metrics[metric_name]]
            b_values = [e.value for e in run_b.metrics[metric_name]]

            if not a_values or not b_values:
                continue

            a_mean = statistics.mean(a_values)
            b_mean = statistics.mean(b_values)
            a_std = statistics.stdev(a_values) if len(a_values) > 1 else 0.0
            b_std = statistics.stdev(b_values) if len(b_values) > 1 else 0.0

            delta = b_mean - a_mean
            delta_pct = (delta / max(abs(a_mean), 1e-8)) * 100

            # Welch's t-test approximation
            se = ((a_std**2 / max(len(a_values), 1)) + (b_std**2 / max(len(b_values), 1))) ** 0.5
            significant = abs(delta) / max(se, 1e-8) > 1.96  # 95% confidence

            comparisons.append(
                MetricComparison(
                    metric_name=metric_name,
                    run_a_mean=a_mean,
                    run_b_mean=b_mean,
                    run_a_std=a_std,
                    run_b_std=b_std,
                    delta=delta,
                    delta_percent=delta_pct,
                    significant=significant,
                )
            )

        summary_lines = [
            f"Comparing {run_a.name} ({run_a_id}) vs {run_b.name} ({run_b_id})",
        ]
        for comp in comparisons:
            direction = "↑" if comp.delta > 0 else "↓" if comp.delta < 0 else "="
            sig = " *" if comp.significant else ""
            summary_lines.append(
                f"  {comp.metric_name}: {comp.run_a_mean:.4f} → {comp.run_b_mean:.4f} "
                f"({direction}{abs(comp.delta_percent):.1f}%){sig}"
            )

        return RunComparison(
            run_a_id=run_a_id,
            run_b_id=run_b_id,
            metric_comparisons=comparisons,
            common_metrics=sorted(common_metrics),
            summary="\n".join(summary_lines),
        )

    def list_runs(
        self,
        status: RunStatus | None = None,
        tag_filter: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """List experiment runs with optional filtering.

        Parameters
        ----------
        status : RunStatus, optional
            Filter by status.
        tag_filter : dict, optional
            Filter by tags (all must match).

        Returns
        -------
        list[dict]
            Run summaries.
        """
        results = []
        for run in self._runs.values():
            if status and run.status != status:
                continue
            if tag_filter:
                if not all(run.tags.get(k) == v for k, v in tag_filter.items()):
                    continue
            results.append(run.summary())
        return results

    def get_run(self, run_id: str) -> ExperimentRun | None:
        """Get a specific run by ID."""
        return self._runs.get(run_id)

    def _resolve_run(self, run_id: str | None) -> ExperimentRun:
        """Resolve run from ID or active run."""
        if run_id:
            run = self._runs.get(run_id)
            if not run:
                raise ValueError(f"Run not found: {run_id}")
            return run
        if self._active_run:
            return self._active_run
        raise ValueError("No active run. Call create_run() or specify run_id.")

    def _save_run_data(self, run: ExperimentRun) -> None:
        """Save run data to disk."""
        run_dir = self.base_dir / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save metrics
        metrics_path = run_dir / "metrics.jsonl"
        with open(metrics_path, "w") as f:
            for name, entries in run.metrics.items():
                for entry in entries:
                    record = {
                        "name": entry.name,
                        "value": entry.value,
                        "step": entry.step,
                        "timestamp": entry.timestamp,
                        "tags": entry.tags,
                    }
                    f.write(json.dumps(record) + "\n")

        # Save summary
        summary_path = run_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(run.summary(), f, indent=2, default=str)

    def _load_index(self) -> None:
        """Load run index from disk."""
        if not self._index_path.exists():
            return

        try:
            with open(self._index_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    run_id = data.get("run_id")
                    if run_id and run_id not in self._runs:
                        # Reconstruct minimal run from index
                        config = RunConfig(
                            seed=data.get("seed", 42),
                            environment={},
                            agent={},
                            training={},
                        )
                        run = ExperimentRun(
                            run_id=run_id,
                            name=data.get("name", ""),
                            config=config,
                            status=RunStatus(data.get("status", "completed")),
                            created_at=data.get("created_at", ""),
                            tags=data.get("tags", {}),
                        )
                        self._runs[run_id] = run
        except Exception as e:
            logger.warning("Failed to load experiment index: %s", e)

    def _append_to_index(self, run: ExperimentRun) -> None:
        """Append run to index file."""
        try:
            with open(self._index_path, "a") as f:
                record = {
                    "run_id": run.run_id,
                    "name": run.name,
                    "status": run.status.value,
                    "seed": run.config.seed,
                    "config_hash": run.config.config_hash,
                    "created_at": run.created_at,
                    "tags": run.tags,
                }
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.warning("Failed to update experiment index: %s", e)


# ---------------------------------------------------------------------------
# Convenience: tracked training loop
# ---------------------------------------------------------------------------


def tracked_training_run(
    name: str,
    seed: int,
    num_episodes: int = 100,
    env_config: dict[str, Any] | None = None,
    agent_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a fully tracked PPO training experiment.

    Wraps the RL training loop with experiment tracking:
    every step logs coherence, reward, and loss metrics.

    Parameters
    ----------
    name : str
        Experiment name.
    seed : int
        Random seed for reproducibility.
    num_episodes : int
        Number of training episodes.
    env_config : dict, optional
        Environment configuration overrides.
    agent_config : dict, optional
        Agent configuration overrides.

    Returns
    -------
    dict
        Run summary with metrics.
    """
    from cohezion.simulation.rl_framework import HihoEnvironment, PPOAgent

    tracker = ExperimentTracker.get_instance()

    config = RunConfig(
        seed=seed,
        environment=env_config or {"grid_size": 64, "max_steps": 500},
        agent=agent_config or {"lr": 3e-4, "gamma": 0.99},
        training={"num_episodes": num_episodes},
    )

    run = tracker.create_run(name=name, config=config)
    tracker.start_run(run.run_id)

    np.random.seed(seed)
    env = HihoEnvironment(
        grid_size=config.environment.get("grid_size", 64),
        max_steps=config.environment.get("max_steps", 500),
    )
    agent = PPOAgent()

    total_steps = 0

    try:
        for episode in range(num_episodes):
            state = env.reset(seed=seed + episode)
            episode_reward = 0.0
            episode_coherence = []

            while True:
                action, log_prob, value = agent.select_action(state)
                next_state, reward, done, info = env.step(action)

                agent.store_transition(state, action, reward, next_state, done, log_prob, value)

                state = next_state
                episode_reward += reward
                total_steps += 1
                episode_coherence.append(info.get("coherence", 0.5))

                if total_steps % 2048 == 0 and len(agent.buffer) >= 32:
                    metrics = agent.update()
                    tracker.log_metrics(
                        {
                            "policy_loss": metrics.get("policy_loss", 0.0),
                            "value_loss": metrics.get("value_loss", 0.0),
                            "entropy": metrics.get("entropy", 0.0),
                        },
                        step=total_steps,
                        run_id=run.run_id,
                    )

                if done:
                    break

            # Log episode metrics
            avg_coh = float(np.mean(episode_coherence)) if episode_coherence else 0.5
            tracker.log_metrics(
                {
                    "episode_reward": episode_reward,
                    "episode_coherence": avg_coh,
                    "episode_length": float(len(episode_coherence)),
                },
                step=episode,
                run_id=run.run_id,
            )

            # Checkpoint every 25 episodes
            if (episode + 1) % 25 == 0:
                tracker.save_checkpoint(
                    state={
                        "policy_w1": agent.policy.w1,
                        "policy_w2": agent.policy.w2,
                        "value_w1": agent.value.w1,
                        "value_w2": agent.value.w2,
                    },
                    step=episode,
                    run_id=run.run_id,
                )

        tracker.end_run(run.run_id, RunStatus.COMPLETED)
    except Exception as e:
        logger.error("Training run failed: %s", e)
        tracker.end_run(run.run_id, RunStatus.FAILED)
        raise

    return run.summary()
