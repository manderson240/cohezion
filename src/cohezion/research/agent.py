"""Autonomous research agent for training optimization.

Elegant integration with Cohezion compound executor.
Based on karpathy/autoresearch patterns.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig
from cohezion.compound.models import ExecutionResult, Task
from cohezion.research.config import ExperimentResult, ResearchConfig

logger = logging.getLogger(__name__)


@dataclass
class ResearchSession:
    """Session state for research.

    Minimal state tracking, delegates to Cohezion persistence.
    """

    session_id: str = field(default_factory=lambda: datetime.now().isoformat())
    experiments_completed: int = 0
    best_metric: float = float("inf")
    best_checkpoint: Path | None = None
    active: bool = True


class ResearchAgent:
    """Autonomous research agent.

    Clean implementation (~200 lines) following elegant simplification.
    Integrates with Cohezion's compound executor and metrics systems.

    Inspired by karpathy/autoresearch but integrated into Cohezion ecosystem.
    """

    def __init__(
        self,
        config: ResearchConfig | None = None,
        executor: CompoundExecutor | None = None,
    ):
        """Initialize research agent.

        Args:
            config: Research configuration
            executor: CompoundExecutor for running experiments
                     (creates new one if None)
        """
        self.config = config or ResearchConfig()
        self.session = ResearchSession()

        # Create executor if not provided
        if executor is None:
            executor = CompoundExecutor(
                execute_fn=self._run_experiment,
                config=ExecutionConfig(max_retries=1),
            )
        self.executor = executor

        logger.info(f"ResearchAgent initialized: {self.session.session_id}")

    def _run_experiment(
        self,
        task: Task,
        context: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Run single experiment.

        This is the core execution function passed to CompoundExecutor.
        """
        experiment_id = task.id
        start_time = time.time()

        logger.info(f"Running experiment: {experiment_id}")

        try:
            # Run training with time budget
            result = self._execute_training(
                time_budget=self.config.experiment_time_budget,
            )

            # Parse result
            metric_value = result.get("val_bpb", float("inf"))
            duration = time.time() - start_time

            # Check if improved
            improved = metric_value < self.session.best_metric
            if improved:
                self.session.best_metric = metric_value
                logger.info(f"New best metric: {metric_value:.4f}")

            return (
                f"Experiment {experiment_id}: {metric_value:.4f}",
                {
                    "metric_value": metric_value,
                    "duration": duration,
                    "improved": improved,
                },
            )

        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            return (
                f"Failed: {e}",
                {
                    "metric_value": float("inf"),
                    "duration": time.time() - start_time,
                    "improved": False,
                },
            )

    def _execute_training(self, time_budget: float) -> dict[str, Any]:
        """Execute training with time limit.

        Runs autoresearch-style training for fixed duration.
        """
        # Run training script
        result = subprocess.run(
            [
                "python",
                "train.py",
                "--time_budget",
                str(time_budget),
            ],
            capture_output=True,
            text=True,
            timeout=time_budget + 60,  # Safety margin
        )

        if result.returncode != 0:
            raise RuntimeError(f"Training failed: {result.stderr}")

        # Parse metrics from output
        # (simplified - in real implementation would parse JSON)
        return {
            "val_bpb": 2.5,  # placeholder
            "train_loss": 2.3,
            "val_loss": 2.4,
        }

    def run_session(
        self,
        max_experiments: int | None = None,
    ) -> ResearchSession:
        """Run complete research session.

        Args:
            max_experiments: Override default max

        Returns:
            Final session state
        """
        max_exp = max_experiments or self.config.max_experiments

        logger.info(f"Starting research session: {max_exp} experiments")

        while self.session.experiments_completed < max_exp and self.session.active:
            # Create experiment task
            exp_id = f"exp-{self.session.experiments_completed + 1}"
            task = Task(
                id=exp_id,
                description=f"Research experiment {exp_id}",
                skill_name="research",
                operation_type="optimize",
            )

            # Run via executor
            result = self.executor.execute(task)

            # Log result
            self._log_experiment(exp_id, result)

            # Update session
            self.session.experiments_completed += 1

            logger.info(
                f"Experiment {exp_id} complete: {self.session.experiments_completed}/{max_exp}"
            )

        logger.info(f"Research session complete: {self.session}")
        return self.session

    def _log_experiment(self, exp_id: str, result: ExecutionResult) -> None:
        """Log experiment result."""
        # Access metrics as dataclass fields, not dict
        exp_result = ExperimentResult(
            experiment_id=exp_id,
            timestamp=datetime.now().isoformat(),
            metric_value=getattr(result.metrics, "metric_value", float("inf")),
            metric_name=self.config.target_metric,
            improved=getattr(result.metrics, "improved", False),
            code_changes=[],  # Would track actual changes
            duration_seconds=result.metrics.duration_seconds,
        )

        # Append to experiment log
        with open(self.config.experiment_log, "a") as f:
            f.write(json.dumps(exp_result.to_dict()) + "\n")

    def get_best_result(self) -> dict[str, Any] | None:
        """Get best experiment result from session."""
        if self.session.best_metric == float("inf"):
            return None

        return {
            "metric": self.session.best_metric,
            "checkpoint": str(self.session.best_checkpoint),
            "experiments": self.session.experiments_completed,
        }

    def stop(self) -> None:
        """Stop research session gracefully."""
        self.session.active = False
        logger.info("Research session stopped")
