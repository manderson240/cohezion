"""Autonomous research agent for training optimization.

Elegant integration with Cohezion compound executor.
Based on karpathy/autoresearch patterns.
"""

from __future__ import annotations

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
from cohezion.reliability import get_circuit  # Issue #8
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
                execute_fn=self._run_experiment_with_circuit_breaker,  # Issue #8
                config=ExecutionConfig(max_retries=1),
            )
        self.executor = executor

        # Circuit breaker for reliability (Issue #8)
        self.circuit = get_circuit("research_agent", failure_threshold=5, recovery_timeout=60)

        logger.info(f"ResearchAgent initialized: {self.session.session_id}")

    def _run_experiment_with_circuit_breaker(
        self,
        task: Task,
        context: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Run experiment with circuit breaker protection (Issue #8)."""
        # Check if circuit is open
        if self.circuit.is_open():
            logger.warning("Circuit breaker open, skipping experiment")
            return "Circuit open", {"error": "Circuit breaker open", "skipped": True}

        try:
            result = self._run_experiment(task, context)
            self.circuit.record_success()
            return result
        except Exception as e:
            self.circuit.record_failure()
            logger.error(f"Experiment failed, circuit breaker recorded: {e}")
            raise

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
                    "coherence": metric_value,
                    "duration_seconds": duration,
                },
            )

        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            return (
                f"Failed: {e}",
                {
                    "coherence": float("inf"),
                    "duration_seconds": time.time() - start_time,
                },
            )

    def _execute_training(self, time_budget: float) -> dict[str, Any]:
        """Execute training with time limit.

        Runs autoresearch-style training for fixed duration.
        """
        # Resolve train script relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        train_script = (project_root / self.config.train_file).resolve()
        if not str(train_script).startswith(str(project_root)):
            raise ValueError(f"Train script outside project root: {self.config.train_file}")

        # Run security guardrails if enabled
        if self.config.enable_guardrails and train_script.exists():
            from cohezion.research.security import CodeChange, ResearchSecurityGuardrails

            guardrails = ResearchSecurityGuardrails()
            change = CodeChange(
                file_path=train_script,
                old_code="",
                new_code=train_script.read_text(),
                change_type="modify",
            )
            validation = guardrails.validate_change(change)
            if not validation.is_valid:
                raise RuntimeError(f"Guardrail blocked execution: {validation.issues}")

        result = subprocess.run(
            [
                "python",
                str(train_script),
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

            logger.info(f"Experiment {exp_id} complete: {self.session.experiments_completed}/{max_exp}")

        logger.info(f"Research session complete: {self.session}")
        return self.session

    def _log_experiment(self, exp_id: str, result: ExecutionResult) -> None:
        """Log experiment result."""
        # Normalize metrics — handle both ExecutionMetrics objects and legacy dicts
        m = result.metrics
        if isinstance(m, dict):
            metric_value = m.get("coherence", float("inf"))
            duration_seconds = m.get("duration_seconds", 0.0)
        else:
            metric_value = getattr(m, "coherence", float("inf"))
            duration_seconds = m.duration_seconds
        improved = metric_value < self.session.best_metric

        exp_result = ExperimentResult(
            experiment_id=exp_id,
            timestamp=datetime.now().isoformat(),
            metric_value=metric_value,
            metric_name=self.config.target_metric,
            improved=improved,
            code_changes=[],  # Would track actual changes
            duration_seconds=duration_seconds,
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
