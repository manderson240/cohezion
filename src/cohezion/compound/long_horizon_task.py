"""Long Horizon Task Engine - Cross-session compound task orchestration.

Allows compound engineering tasks to survive context limits by checkpointing
state to the vault and resuming in new sessions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


def get_context_usage_percent() -> float:
    """Mock helper to check current context window usage."""
    return 50.0


@dataclass
class TaskStepResult:
    """Result of a single step execution."""

    success: bool
    handoff_triggered: bool
    checkpoint_saved: bool


class LongHorizonTask:
    """A compound task that can span multiple sessions."""

    # Biologist: Ensure enough metabolic headroom for meaningful work
    CONTEXT_GUARDRAIL = 80.0
    MIN_HEADROOM_PERCENT = 5.0  # Need at least 5% free context to attempt a step

    def __init__(self, task_id: str, budget_sessions: int = 5, initial_state: dict[str, Any] | None = None):
        """Initialize a long horizon task.

        Args:
            task_id: Unique identifier for the task
            budget_sessions: Max number of sessions allowed
            initial_state: Optional restored state
        """
        self.task_id = task_id
        self.budget_sessions = budget_sessions
        self.steps_completed = 0
        self.total_steps_estimated = 5  # Default

        # Biologist: Track token overhead to adapt headroom
        self._recent_step_overhead: list[float] = []

        if initial_state:
            self.steps_completed = initial_state.get("steps_completed", 0)

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_steps_estimated == 0:
            return 0.0
        return (self.steps_completed / self.total_steps_estimated) * 100.0

    def _calculate_dynamic_headroom(self) -> float:
        """Calculate required context headroom dynamically based on recent steps."""
        if not self._recent_step_overhead:
            return self.MIN_HEADROOM_PERCENT

        # Use 1.5x the average recent overhead to ensure safety
        avg_overhead = sum(self._recent_step_overhead) / len(self._recent_step_overhead)
        return max(self.MIN_HEADROOM_PERCENT, avg_overhead * 1.5)

    def execute_step(self) -> TaskStepResult:
        """Execute the next step of the task, guarding context."""
        context_usage = get_context_usage_percent()

        # Biologist: Check if we have enough headroom for the *overhead* of another step
        dynamic_headroom = self._calculate_dynamic_headroom()

        if context_usage >= (self.CONTEXT_GUARDRAIL - dynamic_headroom):
            logger.warning(
                f"Biologist: Context usage at {context_usage}%. "
                f"Required headroom is {dynamic_headroom}%. Triggering proactive handoff."
            )
            self.save_checkpoint()
            return TaskStepResult(success=True, handoff_triggered=True, checkpoint_saved=True)

        logger.info(f"Executing step {self.steps_completed + 1} for task {self.task_id}")

        success = self._perform_step()
        if success:
            self.steps_completed += 1
            # Record a mock overhead for demonstration (e.g. 1.2% per step)
            self._recent_step_overhead.append(1.2)
            if len(self._recent_step_overhead) > 3:
                self._recent_step_overhead.pop(0)

        return TaskStepResult(success=success, handoff_triggered=False, checkpoint_saved=False)

    def _perform_step(self) -> bool:
        """Internal execution logic."""
        # Stub for the test
        return True

    def save_checkpoint(self) -> dict[str, Any]:
        """Save task state to a checkpoint."""
        checkpoint = {
            "task_id": self.task_id,
            "steps_completed": self.steps_completed,
            "progress_percent": self.progress_percent,
        }
        logger.info(f"Checkpoint saved for {self.task_id}: {checkpoint}")
        return checkpoint

    @classmethod
    def from_checkpoint(cls, checkpoint: dict[str, Any]) -> LongHorizonTask:
        """Restore a task from a checkpoint."""
        return cls(task_id=checkpoint["task_id"], initial_state=checkpoint)
