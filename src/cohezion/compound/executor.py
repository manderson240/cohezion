"""Compound executor with vault-integrated knowledge persistence.

Orchestrates execution lifecycle:
  1. Query vault for experience guidance (prior similar runs)
  2. Execute task with guidance
  3. Log execution trajectory, decisions, metrics to vault
  4. Extract reusable patterns for future runs
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cohezion.compound.vault_execution_logger import (
    ExecutionContext,
    VaultExecutionLogger,
)
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a compound execution."""

    success: bool
    output: str
    metrics: dict[str, Any]
    duration_seconds: float
    vault_experiment_path: str = ""
    vault_decision_paths: list[str] | None = None


class CompoundExecutor:
    """Executor for compound engineering tasks with vault integration.

    Lifecycle:
      1. get_experience_guidance() - Query vault for similar tasks
      2. execute_task() - Run the task with logging
      3. Logs are persisted to vault automatically
      4. extract_patterns() - Save reusable insights
    """

    def __init__(self, mcp_client: MCPClient):
        """Initialize compound executor.

        Args:
            mcp_client: Connected MCPClient for vault operations
        """
        self.mcp_client = mcp_client
        self.logger = VaultExecutionLogger(mcp_client)

    def get_experience_guidance(
        self, task_description: str, project: str = "cohezion"
    ) -> dict[str, Any]:
        """Fetch experience guidance from vault before execution.

        Args:
            task_description: Description of the task to execute
            project: Project name for scoped search

        Returns:
            Dict with relevant_context (decisions, experiments, patterns)
        """
        logger.info("Fetching experience guidance for: %s", task_description)
        result: dict[str, Any] = self.logger.get_experience_guidance(
            task_description=task_description, project=project
        )
        return result

    def execute_task(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str,
        execute_fn: Callable,
        project: str = "cohezion",
    ) -> ExecutionResult:
        """Execute a compound task with vault logging.

        Args:
            task_description: What the task does
            skill_name: Name of the skill being executed
            operation_type: Type of operation
                (generate, analyze, search, transform, persist)
            execute_fn: Callable that executes the task, returns (output, metrics)
            project: Project name for vault logging

        Returns:
            ExecutionResult with success status, output, metrics, vault paths
        """
        start_time = datetime.now()
        start_seconds = time.time()

        # Create execution context
        ctx = ExecutionContext(
            project=project,
            skill_name=skill_name,
            task_description=task_description,
            operation_type=operation_type,
            start_time=start_time,
            mcp_client=self.mcp_client,
        )

        logger.info(
            "Executing task: %s (operation=%s, skill=%s)",
            task_description,
            operation_type,
            skill_name,
        )

        # Step 1: Get experience guidance
        guidance = self.get_experience_guidance(task_description, project)
        logger.debug("Experience guidance: %s", guidance)

        # Step 2: Log execution start
        experiment_path = self.logger.log_execution_start(ctx)

        # Step 3: Execute the task
        success = False
        output = ""
        metrics: dict[str, Any] = {}
        error_msg = ""

        try:
            output, metrics = execute_fn(guidance)
            success = True
            logger.info("Task completed successfully")
        except Exception as e:
            error_msg = str(e)
            output = f"Error: {error_msg}"
            metrics = {"error": error_msg}
            logger.error("Task failed: %s", error_msg, exc_info=True)

        duration_seconds = time.time() - start_seconds
        metrics["duration_seconds"] = duration_seconds

        # Step 4: Log execution results
        self.logger.log_execution_result(
            experiment_path=experiment_path,
            success=success,
            output=output,
            metrics=metrics,
        )

        # Step 5: If successful, extract patterns
        decision_paths = []
        if success and experiment_path:
            try:
                pattern_path = self.logger.extract_execution_pattern(
                    source_path=experiment_path,
                    pattern_name=f"{skill_name}_{operation_type}_success",
                    description=f"Successful execution pattern for {skill_name} "
                    f"operation: {operation_type}. "
                    f"Task: {task_description[:100]}",
                    code_example=f"Result metrics: {json.dumps(metrics, indent=2)}",
                    domain="compound-engineering",
                )
                if pattern_path:
                    decision_paths.append(pattern_path)
            except Exception as e:
                logger.warning("Failed to extract pattern: %s", e, exc_info=True)

        return ExecutionResult(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            vault_experiment_path=experiment_path,
            vault_decision_paths=decision_paths,
        )

    def log_inflection_point(
        self,
        title: str,
        context: str,
        decision: str,
        rationale: str,
        project: str = "cohezion",
    ) -> str:
        """Log a critical decision point (called by InflectionDetector).

        Args:
            title: Decision title
            context: What led to this decision
            decision: The decision made
            rationale: Why this decision was made
            project: Project name

        Returns:
            Path to vault decision file
        """
        logger.info("Logging inflection point: %s", title)
        result: str = self.logger.log_decision_point(
            project=project,
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
        )
        return result


class ExecutorFactory:
    """Factory for creating compound executors with vault integration."""

    _instance: CompoundExecutor | None = None

    @staticmethod
    def create(mcp_client: MCPClient) -> CompoundExecutor:
        """Create a new compound executor.

        Args:
            mcp_client: Connected MCP client

        Returns:
            CompoundExecutor instance
        """
        return CompoundExecutor(mcp_client)

    @staticmethod
    def get_singleton(mcp_client: MCPClient) -> CompoundExecutor:
        """Get or create singleton executor.

        Args:
            mcp_client: Connected MCP client

        Returns:
            Singleton CompoundExecutor instance
        """
        if ExecutorFactory._instance is None:
            ExecutorFactory._instance = CompoundExecutor(mcp_client)
        return ExecutorFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        ExecutorFactory._instance = None
