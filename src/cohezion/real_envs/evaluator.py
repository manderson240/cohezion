"""Rigorous evaluation harness for real environment tasks.

Verifies actual outcomes (not just action success) for agent tasks.
Checks file contents, API responses, browser states, and more.
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from cohezion.real_envs.browser_env import (
    BrowserEnvironment,
    BrowserObservation,
    BrowserAction,
)
from cohezion.real_envs.shell_env import ShellEnvironment, ShellObservation, ShellAction
from cohezion.real_envs.api_env import APIEnvironment, APIObservation, APIAction


logger = logging.getLogger(__name__)


@dataclass
class TaskVerification:
    """Result of verifying a task's completion criteria."""

    criterion_name: str
    passed: bool
    actual_value: Any = None
    expected_value: Any = None
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_name": self.criterion_name,
            "passed": self.passed,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "details": self.details,
        }


@dataclass
class TaskEvaluation:
    """Complete evaluation of a task execution."""

    task_id: str
    task_description: str
    all_criteria_passed: bool
    criteria: list[TaskVerification]
    reward: float
    metrics: dict[str, Any] = field(default_factory=dict)
    execution_trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "all_criteria_passed": self.all_criteria_passed,
            "pass_rate": sum(1 for c in self.criteria if c.passed) / len(self.criteria)
            if self.criteria
            else 0,
            "criteria": [c.to_dict() for c in self.criteria],
            "reward": self.reward,
            "metrics": self.metrics,
        }


class TaskCriterion(ABC):
    """Abstract base for task completion criteria."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    async def verify(self, environment: Any, trajectory: list[Any]) -> TaskVerification:
        """Verify this criterion against the environment state."""
        pass


class FileExistsCriterion(TaskCriterion):
    """Verify a file exists."""

    def __init__(self, relative_path: str, description: str = ""):
        super().__init__(f"file_exists:{relative_path}", description)
        self.relative_path = relative_path

    async def verify(
        self, environment: ShellEnvironment, trajectory: list[Any]
    ) -> TaskVerification:
        target_path = environment.working_dir / self.relative_path
        exists = target_path.exists()

        return TaskVerification(
            criterion_name=self.name,
            passed=exists,
            actual_value=exists,
            expected_value=True,
            details=f"File {self.relative_path} {'exists' if exists else 'does not exist'}",
        )


class FileContentCriterion(TaskCriterion):
    """Verify file content matches expected pattern."""

    def __init__(
        self,
        relative_path: str,
        expected_content: str | None = None,
        expected_pattern: str | None = None,
        description: str = "",
    ):
        super().__init__(f"file_content:{relative_path}", description)
        self.relative_path = relative_path
        self.expected_content = expected_content
        self.expected_pattern = expected_pattern

    async def verify(
        self, environment: ShellEnvironment, trajectory: list[Any]
    ) -> TaskVerification:
        target_path = environment.working_dir / self.relative_path

        if not target_path.exists():
            return TaskVerification(
                criterion_name=self.name,
                passed=False,
                actual_value=None,
                expected_value=self.expected_content or self.expected_pattern,
                details=f"File {self.relative_path} does not exist",
            )

        try:
            content = target_path.read_text()
        except Exception as e:
            return TaskVerification(
                criterion_name=self.name,
                passed=False,
                actual_value=str(e),
                expected_value=self.expected_content or self.expected_pattern,
                details=f"Failed to read file: {e}",
            )

        if self.expected_content is not None:
            passed = self.expected_content in content
            return TaskVerification(
                criterion_name=self.name,
                passed=passed,
                actual_value=content[:200] + "..." if len(content) > 200 else content,
                expected_value=self.expected_content,
                details=f"Expected content {'found' if passed else 'not found'}",
            )

        if self.expected_pattern is not None:
            match = re.search(self.expected_pattern, content)
            passed = match is not None
            return TaskVerification(
                criterion_name=self.name,
                passed=passed,
                actual_value=content[:200] + "..." if len(content) > 200 else content,
                expected_value=self.expected_pattern,
                details=f"Pattern {'matched' if passed else 'not matched'}",
            )

        return TaskVerification(
            criterion_name=self.name,
            passed=True,
            actual_value=content[:200] + "..." if len(content) > 200 else content,
            expected_value="any content",
            details="File has content",
        )


class CommandSucceededCriterion(TaskCriterion):
    """Verify at least one command in trajectory succeeded."""

    def __init__(self, command_pattern: str | None = None, description: str = ""):
        super().__init__("command_succeeded", description)
        self.command_pattern = command_pattern

    async def verify(
        self, environment: ShellEnvironment, trajectory: list[Any]
    ) -> TaskVerification:
        matching_steps = trajectory

        if self.command_pattern:
            matching_steps = [
                s
                for s in trajectory
                if hasattr(s, "action")
                and self.command_pattern in str(s.action.parameters.get("command", ""))
            ]

        succeeded = any(
            hasattr(s, "observation") and s.observation.success for s in matching_steps
        )

        return TaskVerification(
            criterion_name=self.name,
            passed=succeeded,
            actual_value=succeeded,
            expected_value=True,
            details=f"Command {'succeeded' if succeeded else 'did not succeed'}",
        )


class URLContentCriterion(TaskCriterion):
    """Verify browser loaded page with expected content."""

    def __init__(
        self,
        expected_url_pattern: str | None = None,
        expected_title_pattern: str | None = None,
        expected_text_pattern: str | None = None,
        description: str = "",
    ):
        super().__init__("url_content", description)
        self.expected_url_pattern = expected_url_pattern
        self.expected_title_pattern = expected_title_pattern
        self.expected_text_pattern = expected_text_pattern

    async def verify(
        self, environment: BrowserEnvironment, trajectory: list[Any]
    ) -> TaskVerification:
        state = environment.get_state()

        checks = []

        if self.expected_url_pattern:
            url_match = re.search(self.expected_url_pattern, state.url) is not None
            checks.append(("url_pattern", url_match, self.expected_url_pattern))

        if self.expected_title_pattern:
            title_match = (
                re.search(self.expected_title_pattern, state.title) is not None
            )
            checks.append(("title_pattern", title_match, self.expected_title_pattern))

        all_passed = all(c[1] for c in checks) if checks else True

        details = "; ".join(f"{c[0]}: {'✓' if c[1] else '✗'}" for c in checks)

        return TaskVerification(
            criterion_name=self.name,
            passed=all_passed,
            actual_value={"url": state.url, "title": state.title},
            expected_value={
                "url_pattern": self.expected_url_pattern,
                "title_pattern": self.expected_title_pattern,
            },
            details=details,
        )


class APIResponseCriterion(TaskCriterion):
    """Verify API returned expected response."""

    def __init__(
        self,
        expected_status_code: int | None = None,
        expected_json_path: str | None = None,
        expected_json_value: Any = None,
        description: str = "",
    ):
        super().__init__("api_response", description)
        self.expected_status_code = expected_status_code
        self.expected_json_path = expected_json_path
        self.expected_json_value = expected_json_value

    async def verify(
        self, environment: APIEnvironment, trajectory: list[Any]
    ) -> TaskVerification:
        # Find most recent HTTP observation
        http_steps = [
            s
            for s in reversed(trajectory)
            if hasattr(s, "observation") and hasattr(s.observation, "status_code")
        ]

        if not http_steps:
            return TaskVerification(
                criterion_name=self.name,
                passed=False,
                actual_value=None,
                expected_value=self.expected_status_code,
                details="No HTTP requests in trajectory",
            )

        last_step = http_steps[0]
        obs = last_step.observation

        checks = []

        if self.expected_status_code is not None:
            status_match = obs.status_code == self.expected_status_code
            checks.append(("status_code", status_match, self.expected_status_code))

        if self.expected_json_path is not None and obs.response_json:
            value = self._get_nested_value(obs.response_json, self.expected_json_path)
            json_match = value == self.expected_json_value
            checks.append(("json_value", json_match, self.expected_json_value))

        all_passed = all(c[1] for c in checks) if checks else True

        return TaskVerification(
            criterion_name=self.name,
            passed=all_passed,
            actual_value={
                "status_code": obs.status_code,
                "response_json": obs.response_json,
            },
            expected_value={
                "status_code": self.expected_status_code,
                "json_path": self.expected_json_path,
                "json_value": self.expected_json_value,
            },
            details=f"Last request to {obs.request_url}",
        )

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get value from nested dict using dot notation."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


class RealEnvironmentEvaluator:
    """Evaluates agent performance on real environment tasks.

    Unlike action-based evaluation, this verifies actual outcomes:
    - File contents match expected patterns
    - API responses contain expected data
    - Browser pages show expected content
    - Commands produce expected results

    Example:
        ```python
        evaluator = RealEnvironmentEvaluator()

        # Define task with completion criteria
        task = EvaluatedTask(
            task_id="create_flask_app",
            description="Create a minimal Flask application",
            environment_type="shell",
            criteria=[
                FileExistsCriterion("app.py"),
                FileContentCriterion("app.py", expected_pattern=r"from flask import Flask"),
                FileContentCriterion("app.py", expected_pattern=r"@app.route"),
            ],
        )

        # Run agent and evaluate
        env = ShellEnvironment(task.description)
        # ... agent executes actions ...

        result = await evaluator.evaluate_task(task, env, env.trajectory)
        print(f"Task passed: {result.all_criteria_passed}")
        print(f"Reward: {result.reward}")
        ```
    """

    def __init__(self, output_dir: str = "data/real_envs/evaluations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def evaluate_task(
        self,
        task: "EvaluatedTask",
        environment: Any,
        trajectory: list[Any],
    ) -> TaskEvaluation:
        """Evaluate a task execution against its criteria."""
        logger.info(f"Evaluating task: {task.task_id}")

        criteria_results = []

        for criterion in task.criteria:
            try:
                result = await criterion.verify(environment, trajectory)
                criteria_results.append(result)
            except Exception as e:
                logger.error(f"Criterion verification failed: {e}")
                criteria_results.append(
                    TaskVerification(
                        criterion_name=criterion.name,
                        passed=False,
                        details=f"Verification error: {e}",
                    )
                )

        # Compute overall results
        all_passed = all(r.passed for r in criteria_results)
        pass_rate = (
            sum(1 for r in criteria_results if r.passed) / len(criteria_results)
            if criteria_results
            else 0
        )

        # Reward based on pass rate and efficiency
        efficiency_bonus = (
            max(0, 1.0 - (len(trajectory) / task.expected_steps))
            if task.expected_steps > 0
            else 0
        )
        reward = pass_rate * 0.8 + efficiency_bonus * 0.2

        # Collect metrics
        metrics = {
            "total_steps": len(trajectory),
            "expected_steps": task.expected_steps,
            "pass_rate": pass_rate,
            "criteria_count": len(criteria_results),
            "passed_criteria": sum(1 for r in criteria_results if r.passed),
        }

        evaluation = TaskEvaluation(
            task_id=task.task_id,
            task_description=task.description,
            all_criteria_passed=all_passed,
            criteria=criteria_results,
            reward=reward,
            metrics=metrics,
            execution_trace=[step.to_dict() for step in trajectory]
            if hasattr(trajectory[0], "to_dict")
            else [],
        )

        # Save evaluation
        self._save_evaluation(evaluation)

        logger.info(
            f"Task {task.task_id} evaluation complete: "
            f"passed={all_passed}, reward={reward:.2f}"
        )

        return evaluation

    def _save_evaluation(self, evaluation: TaskEvaluation) -> Path:
        """Save evaluation to disk."""
        filepath = self.output_dir / f"{evaluation.task_id}_{int(time.time())}.json"

        with open(filepath, "w") as f:
            json.dump(evaluation.to_dict(), f, indent=2, default=str)

        return filepath


@dataclass
class EvaluatedTask:
    """A task definition with evaluation criteria."""

    task_id: str
    description: str
    environment_type: str  # "shell", "browser", "api", "multi"
    criteria: list[TaskCriterion] = field(default_factory=list)
    expected_steps: int = 10
    max_steps: int = 50
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "environment_type": self.environment_type,
            "criteria": [
                {"name": c.name, "description": c.description} for c in self.criteria
            ],
            "expected_steps": self.expected_steps,
            "max_steps": self.max_steps,
            "metadata": self.metadata,
        }
