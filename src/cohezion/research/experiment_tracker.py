"""Research experiment tracking module.

Provides MLflow/WandB integration for tracking training metrics, benchmark results,
and system resources. Gracefully handles cases when MLflow/WandB are not installed.
"""

import importlib.util
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Self


logger = logging.getLogger(__name__)


class TrackerBackend(Enum):
    """Available tracking backends."""

    MLFLOW = "mlflow"
    WANDB = "wandb"
    NONE = "none"


@dataclass
class TrainingMetrics:
    """Training metrics for a single epoch."""

    epoch: int
    loss: float
    mse: float | None = None
    kl: float | None = None
    coherence: float | None = None
    coherence_loss: float | None = None
    lr: float | None = None
    elapsed_s: float | None = None
    step: int | None = None


@dataclass
class BenchmarkResults:
    """Benchmark evaluation results."""

    benchmark: str
    model_name: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SystemMetrics:
    """System resource metrics."""

    rss_gb: float
    available_ram_gb: float
    cpu_percent: float
    gpu_memory_gb: float | None = None
    throughput: float | None = None
    timestamp: float = field(default_factory=time.time)


class ExperimentTracker:
    """Unified experiment tracking with MLflow/WandB support.

    Provides a simple API for logging metrics, parameters, and artifacts
    across different backends. Falls back to local file storage when
    MLflow/WandB are not available.

    Usage:
        tracker = ExperimentTracker("flume_training")
        tracker.log_params({"lr": 1e-3, "epochs": 50})
        tracker.log_metric("loss", 0.15)
        tracker.log_artifact("model.pt")
    """

    def __init__(
        self,
        experiment_name: str,
        backend: TrackerBackend | str | None = None,
        run_name: str | None = None,
        tracking_uri: str | None = None,
    ):
        """Initialize experiment tracker.

        Args:
            experiment_name: Name of the experiment
            backend: Tracking backend ("mlflow", "wandb", or "none").
                     Auto-detects if None.
            run_name: Optional name for this specific run
            tracking_uri: Custom tracking URI for MLflow
        """
        self.experiment_name = experiment_name
        self.run_name = run_name
        self.tracking_uri = tracking_uri

        if backend is None:
            backend = self._detect_backend()
        elif isinstance(backend, str):
            backend = TrackerBackend(backend.lower())

        self.backend = backend
        self._client = None
        self._wandb_run = None
        self._local_log_dir = Path("data/experiments") / experiment_name
        self._local_log_dir.mkdir(parents=True, exist_ok=True)

        self._init_backend()

    def _detect_backend(self) -> TrackerBackend:
        """Auto-detect available tracking backend."""
        if (
            os.environ.get("MLFLOW_TRACKING_URI")
            or os.environ.get("DISABLE_MLFLOW", "").lower() != "true"
        ) and importlib.util.find_spec("mlflow") is not None:
            return TrackerBackend.MLFLOW

        if (
            os.environ.get("WANDB_API_KEY")
            or os.environ.get("DISABLE_WANDB", "").lower() != "true"
        ) and importlib.util.find_spec("wandb") is not None:
            return TrackerBackend.WANDB

        logger.info("No MLflow/WandB available, using local file storage")
        return TrackerBackend.NONE

    def _init_backend(self) -> None:
        """Initialize the selected tracking backend."""
        if self.backend == TrackerBackend.MLFLOW:
            try:
                import mlflow

                mlflow.set_experiment(self.experiment_name)
                if self.tracking_uri:
                    mlflow.set_tracking_uri(self.tracking_uri)
                self._client = mlflow
                self._run = mlflow.start_run(run_name=self.run_name)
                logger.info(f"MLflow tracking initialized for {self.experiment_name}")
            except ImportError:
                logger.warning("MLflow not installed, falling back to local storage")
                self.backend = TrackerBackend.NONE
                self._init_backend()
            except Exception as e:
                logger.warning(
                    f"Failed to init MLflow: {e}, falling back to local storage"
                )
                self.backend = TrackerBackend.NONE
                self._init_backend()

        elif self.backend == TrackerBackend.WANDB:
            try:
                import wandb

                self._wandb_run = wandb.init(
                    project=self.experiment_name,
                    name=self.run_name,
                    config={},
                )
                self._client = wandb
                logger.info(f"WandB tracking initialized for {self.experiment_name}")
            except ImportError:
                logger.warning("WandB not installed, falling back to local storage")
                self.backend = TrackerBackend.NONE
                self._init_backend()
            except Exception as e:
                logger.warning(
                    f"Failed to init WandB: {e}, falling back to local storage"
                )
                self.backend = TrackerBackend.NONE
                self._init_backend()

        else:
            self._run = None
            logger.info(f"Using local file storage at {self._local_log_dir}")

    def log_metric(self, name: str, value: float, step: int | None = None) -> None:
        """Log a single metric value.

        Args:
            name: Metric name
            value: Metric value
            step: Optional step/epoch number
        """
        if self.backend == TrackerBackend.MLFLOW and self._client:
            self._client.log_metric(
                self._client.Metric(
                    name, value, step=step or 0, timestamp=int(time.time() * 1000)
                )
            )
        elif self.backend == TrackerBackend.WANDB and self._client:
            self._client.log({name: value}, step=step)
        else:
            self._log_locally({"metric": name, "value": value, "step": step})

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Log multiple metrics at once.

        Args:
            metrics: Dictionary of metric names to values
            step: Optional step/epoch number
        """
        if self.backend == TrackerBackend.MLFLOW and self._client:
            for name, value in metrics.items():
                self._client.log_metric(
                    self._client.Metric(
                        name,
                        float(value),
                        step=step or 0,
                        timestamp=int(time.time() * 1000),
                    )
                )
        elif self.backend == TrackerBackend.WANDB and self._client:
            self._client.log(metrics, step=step)
        else:
            self._log_locally({"metrics": metrics, "step": step})

    def log_params(self, params: dict[str, Any]) -> None:
        """Log experiment parameters.

        Args:
            params: Dictionary of parameter names to values
        """
        if self.backend == TrackerBackend.MLFLOW and self._client:
            self._client.log_params(params)
        elif self.backend == TrackerBackend.WANDB and self._client:
            self._client.config.update(params)
        else:
            self._log_locally({"params": params})

    def log_artifact(self, local_path: str, artifact_name: str | None = None) -> None:
        """Log an artifact (file or directory).

        Args:
            local_path: Path to the local file/directory
            artifact_name: Optional name for the artifact
        """
        path = Path(local_path)
        if not path.exists():
            logger.warning(f"Artifact not found: {local_path}")
            return

        if self.backend == TrackerBackend.MLFLOW and self._client:
            self._client.log_artifact(local_path, artifact_name or path.name)
        elif self.backend == TrackerBackend.WANDB and self._client:
            self._client.log(
                artifact_name or path.name, self._client.Artifact(path.name)
            )
        else:
            dest = self._local_log_dir / (artifact_name or path.name)
            import shutil

            if path.is_dir():
                shutil.copytree(path, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(path, dest)
            logger.debug(f"Artifact saved locally: {dest}")

    def _log_locally(self, data: dict[str, Any]) -> None:
        """Log data to local JSON file."""
        log_file = self._local_log_dir / "metrics.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps({"timestamp": time.time(), **data}) + "\n")

    def log_training_metrics(self, metrics: TrainingMetrics) -> None:
        """Log FLUME training metrics.

        Args:
            metrics: Training metrics from an epoch
        """
        log_data: dict[str, float] = {
            "epoch": metrics.epoch,
            "loss": metrics.loss,
        }

        if metrics.mse is not None:
            log_data["mse"] = metrics.mse
        if metrics.kl is not None:
            log_data["kl"] = metrics.kl
        if metrics.coherence is not None:
            log_data["coherence"] = metrics.coherence
        if metrics.coherence_loss is not None:
            log_data["coherence_loss"] = metrics.coherence_loss
        if metrics.lr is not None:
            log_data["lr"] = metrics.lr
        if metrics.elapsed_s is not None:
            log_data["elapsed_s"] = metrics.elapsed_s
        if metrics.step is not None:
            log_data["step"] = metrics.step

        self.log_metrics(log_data, step=metrics.epoch)

    def log_benchmark_results(self, results: BenchmarkResults) -> None:
        """Log benchmark evaluation results.

        Args:
            results: Benchmark results
        """
        self.log_metric(f"{results.benchmark}/score", results.score)
        self.log_params({f"{results.benchmark}/model": results.model_name})
        if results.details:
            self._log_locally(
                {"benchmark": results.benchmark, "results": results.details}
            )

    def log_system_metrics(self, metrics: SystemMetrics) -> None:
        """Log system resource metrics.

        Args:
            metrics: System metrics snapshot
        """
        log_data: dict[str, float] = {
            "rss_gb": metrics.rss_gb,
            "available_ram_gb": metrics.available_ram_gb,
            "cpu_percent": metrics.cpu_percent,
        }

        if metrics.gpu_memory_gb is not None:
            log_data["gpu_memory_gb"] = metrics.gpu_memory_gb
        if metrics.throughput is not None:
            log_data["throughput"] = metrics.throughput

        self.log_metrics(log_data)

    def flush(self) -> None:
        """Force flush any buffered data."""
        if self.backend == TrackerBackend.MLFLOW and self._client:
            pass
        elif self.backend == TrackerBackend.WANDB and self._client:
            self._client.log({})

    def finish(self) -> None:
        """Finish the current run."""
        self.flush()

        if self.backend == TrackerBackend.MLFLOW and self._client:
            self._client.end_run()
        elif self.backend == TrackerBackend.WANDB and self._wandb_run:
            self._wandb_run.finish()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.finish()


class FLUMETrainingTracker:
    """Auto-tracking wrapper for FLUME training loops.

    Provides convenient integration with FlumeVAETrainer to automatically
    log metrics during training without modifying the trainer itself.

    Usage:
        tracker = FLUMETrainingTracker("flume_exp", experiment_name="flume_v1")
        metrics = trainer.train()
        tracker.log_training_history(metrics)
    """

    def __init__(
        self,
        experiment_name: str,
        backend: TrackerBackend | str | None = None,
        run_name: str | None = None,
    ):
        """Initialize FLUME training tracker.

        Args:
            experiment_name: Name of the experiment
            backend: Tracking backend
            run_name: Optional run name
        """
        self.experiment_tracker = ExperimentTracker(
            experiment_name=experiment_name,
            backend=backend,
            run_name=run_name,
        )
        self._start_time: float | None = None

    def log_params(
        self,
        lr: float,
        epochs: int,
        batch_size: int,
        z_dim: int = 256,
        kl_weight: float = 0.1,
        coherence_weight: float = 0.05,
    ) -> None:
        """Log FLUME training parameters.

        Args Learning rate
            epochs: Number of training:
            lr: epochs
            batch_size: Batch size
            z_dim: Latent dimension
            kl_weight: KL divergence weight
            coherence_weight: Coherence loss weight
        """
        self.experiment_tracker.log_params(
            {
                "lr": lr,
                "epochs": epochs,
                "batch_size": batch_size,
                "z_dim": z_dim,
                "kl_weight": kl_weight,
                "coherence_weight": coherence_weight,
            }
        )

    def log_training_history(self, epoch_metrics: list[dict[str, Any]]) -> None:
        """Log complete training history.

        Args:
            epoch_metrics: List of per-epoch metric dictionaries from FlumeVAETrainer
        """
        for epoch_data in epoch_metrics:
            metrics = TrainingMetrics(
                epoch=int(epoch_data.get("epoch", 0)),
                loss=float(epoch_data.get("total", epoch_data.get("loss", 0))),
                mse=epoch_data.get("mse"),
                kl=epoch_data.get("kl"),
                coherence_loss=epoch_data.get("coherence_loss"),
                lr=epoch_data.get("lr"),
                elapsed_s=epoch_data.get("elapsed_s"),
            )
            self.experiment_tracker.log_training_metrics(metrics)

    def log_single_epoch(self, epoch: int, metrics: dict[str, float]) -> None:
        """Log a single training epoch.

        Args:
            epoch: Epoch number
            metrics: Dictionary of metric values
        """
        training_metrics = TrainingMetrics(
            epoch=epoch,
            loss=metrics.get("total", metrics.get("loss", 0)),
            mse=metrics.get("mse"),
            kl=metrics.get("kl"),
            coherence_loss=metrics.get("coherence_loss"),
            lr=metrics.get("lr"),
            elapsed_s=metrics.get("elapsed_s"),
        )
        self.experiment_tracker.log_training_metrics(training_metrics)

    def finish(self) -> None:
        """Finish tracking."""
        self.experiment_tracker.finish()


def get_system_metrics() -> SystemMetrics:
    """Get current system resource metrics.

    Returns:
        Current system metrics snapshot
    """
    rss_gb = 0.0
    available_ram_gb = 64.0
    cpu_percent = 0.0

    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss_kb = int(line.split()[1])
                    rss_gb = rss_kb / (1024 * 1024)
                    break
    except (OSError, ValueError):
        pass

    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = int(parts[1])
            available_ram_gb = meminfo.get("MemAvailable", 0) / (1024 * 1024)
    except (OSError, ValueError):
        pass

    try:
        with open("/proc/loadavg") as f:
            load_1m = float(f.read().split()[0])
            import os

            n_cpus = os.cpu_count() or 32
            cpu_percent = min(100.0, (load_1m / n_cpus) * 100.0)
    except (OSError, ValueError):
        pass

    return SystemMetrics(
        rss_gb=rss_gb,
        available_ram_gb=available_ram_gb,
        gpu_memory_gb=None,
        cpu_percent=cpu_percent,
    )
