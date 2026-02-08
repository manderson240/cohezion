"""Automatic execution logging to Obsidian vault for compound engineering.

Logs execution trajectories, decisions, and patterns to the knowledge vault
for experience-guided future runs. Integrates with MCP client for persistence.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for a compound engineering execution."""

    project: str
    skill_name: str
    task_description: str
    operation_type: str  # "generate", "analyze", "search", "transform", "persist"
    start_time: datetime
    mcp_client: MCPClient


class VaultExecutionLogger:
    """Auto-logs compound execution results to knowledge vault.

    Integrates with Cloud Vault MCP server to:
    1. Search for relevant prior executions via vault_find_relevant_context()
    2. Log new executions as vault experiments
    3. Capture inflection points as decisions
    4. Extract reusable patterns post-execution
    """

    def __init__(self, mcp_client: MCPClient):
        """Initialize execution logger.

        Args:
            mcp_client: Connected MCPClient instance
        """
        self.mcp_client = mcp_client

    def get_experience_guidance(
        self, task_description: str, project: str = "cohezion"
    ) -> dict[str, Any]:
        """Search vault for prior executions on similar tasks.

        Args:
            task_description: Description of the task
            project: Project name for scoped search

        Returns:
            Dict with relevant_experiments, relevant_decisions, relevant_patterns
        """
        try:
            context = self.mcp_client.vault_find_relevant_context(
                query=task_description, project=project
            )
            return {"relevant_context": context}
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Failed to fetch experience guidance: %s", e, exc_info=True
            )
            return {"relevant_context": [], "error": str(e)}

    def log_execution_start(self, ctx: ExecutionContext) -> str:
        """Log execution start as experiment hypothesis.

        Args:
            ctx: ExecutionContext with task details

        Returns:
            Experiment file path in vault
        """
        try:
            hypothesis = (
                f"Running {ctx.operation_type} operation on skill '{ctx.skill_name}' "
                f"for task: {ctx.task_description}"
            )
            method = (
                f"Using CompoundExecutor with operation type: {ctx.operation_type}. "
                f"Task: {ctx.task_description}"
            )
            title = f"{ctx.skill_name}_{ctx.operation_type}_{ctx.start_time.isoformat()}"

            result_path = self.mcp_client.vault_log_experiment(
                project=ctx.project,
                hypothesis=hypothesis,
                method=method,
                title=title,
                result="",  # Will be filled post-execution
                learnings="",  # Will be filled post-execution
            )
            logger.debug("Logged execution start: %s", result_path)
            return result_path
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to log execution start: %s", e, exc_info=True)
            return ""

    def log_execution_result(
        self,
        experiment_path: str,
        success: bool,
        output: str,
        metrics: dict[str, Any],
    ) -> None:
        """Log execution results back to vault.

        Args:
            experiment_path: Path to vault experiment file
            success: Whether execution succeeded
            output: Execution output/results
            metrics: Metrics dict (token_count, latency, etc.)
        """
        if not experiment_path:
            return

        try:
            result_summary = f"Success: {success}\nMetrics: {json.dumps(metrics, indent=2)}\n\nOutput:\n{output[:500]}"  # noqa: E501
            learnings = (
                f"Execution completed with success={success}. "
                f"Token efficiency: {metrics.get('token_efficiency', 'N/A')}. "
                f"Coherence: {metrics.get('coherence', 'N/A')}."
            )

            edits = [
                {
                    "operation": "find_replace",
                    "find": '"result": ""',
                    "replace": f'"result": "{result_summary}"',
                },
                {
                    "operation": "find_replace",
                    "find": '"learnings": ""',
                    "replace": f'"learnings": "{learnings}"',
                },
            ]

            self.mcp_client.vault_edit(path=experiment_path, edits=edits)
            logger.debug("Updated experiment with results: %s", experiment_path)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to log execution result: %s", e, exc_info=True)

    def log_decision_point(
        self,
        project: str,
        title: str,
        context: str,
        decision: str,
        rationale: str,
    ) -> str:
        """Log a critical decision during execution.

        Called by InflectionDetector at warning/critical severity.

        Args:
            project: Project name
            title: Decision title
            context: What led to this decision
            decision: The decision made
            rationale: Why this decision was made

        Returns:
            Decision file path
        """
        try:
            result_path = self.mcp_client.vault_log_decision(
                project=project,
                title=title,
                context=context,
                decision=decision,
                rationale=rationale,
            )
            logger.debug("Logged decision point: %s", result_path)
            return result_path
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to log decision: %s", e, exc_info=True)
            return ""

    def extract_execution_pattern(
        self,
        source_path: str,
        pattern_name: str,
        description: str,
        code_example: str = "",
        domain: str = "general",
    ) -> str:
        """Extract and save reusable pattern from execution.

        Called post-execution to capture learnings for future use.

        Args:
            source_path: Path to source experiment/note
            pattern_name: Name of the pattern
            description: Pattern description
            code_example: Optional code example
            domain: Domain tag (e.g., "compound-engineering", "rl")

        Returns:
            Pattern file path
        """
        try:
            result_path = self.mcp_client.vault_extract_pattern(
                source_path=source_path,
                pattern_name=pattern_name,
                description=description,
                code_example=code_example,
                domain=domain,
            )
            logger.debug("Extracted pattern: %s", result_path)
            return result_path
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to extract pattern: %s", e, exc_info=True)
            return ""
