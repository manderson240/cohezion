"""Cohezion-AgentVerse integration adapter.

Wraps Cohezion skills as AgentVerse-compatible agents for multi-agent
coordination with coherence-aware execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.core.mcp_client import MCPClient

logger = logging.getLogger(__name__)


_TASK_MODEL_MAP: dict[str, str] = {
    "code": "qwen3-coder:30b",
    "implement": "qwen3-coder:30b",
    "write": "qwen3-coder:30b",
    "test": "phi3:mini",
    "verify": "phi3:mini",
    "lint": "phi3:mini",
    "review": "phi3:mini",
    "research": "deepseek-r1:70b",
    "analyze": "deepseek-r1:70b",
    "architect": "deepseek-r1:70b",
}

_ROLE_TOOLS: dict[str, tuple[list[str], list[str]]] = {
    "implementer": (["Read", "Glob", "Grep", "Bash", "Edit", "Write"], ["NotebookEdit"]),
    "reviewer": (["Read", "Glob", "Grep"], ["Bash", "Edit", "Write", "NotebookEdit"]),
    "researcher": (["Read", "Glob", "Grep", "Write"], ["Bash", "NotebookEdit"]),
    "tester": (["Bash", "Read", "Glob", "Grep"], ["Edit", "Write", "NotebookEdit"]),
}


@dataclass
class CohezionAgentAdapter:
    """Adapter that wraps Cohezion skills as AgentVerse agents.

    This adapter allows Cohezion's compound execution pipeline (with
    coherence tracking, skill refinement, and vault integration) to
    be used as agents within AgentVerse's multi-agent frameworks.

    Parameters
    ----------
    skill_name : str
        Name of the Cohezion skill to wrap (e.g., "python_PRIME")
    mcp_client : MCPClient
        Connected MCP client for vault operations
    executor : CompoundExecutor
        CompoundExecutor instance for task execution
    role : str
        Agent role: "implementer", "reviewer", "researcher", "tester"
        Defaults to "implementer".

    Attributes
    ----------
    message_history : list[dict]
        Tracks agent message history for AgentVerse compatibility
    """

    skill_name: str
    mcp_client: MCPClient
    executor: Any
    role: str = "implementer"
    message_history: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate role and initialize tools."""
        if self.role not in _ROLE_TOOLS:
            logger.warning(
                "Unknown role %s, defaulting to implementer",
                self.role,
            )
            self.role = "implementer"

    def step(self, task_description: str) -> Any:
        """Execute a single step/task through Cohezion's compound executor.

        Parameters
        ----------
        task_description : str
            Natural language description of the task

        Returns
        -------
        ExecutionResult
            Cohezion execution result with coherence metrics
        """
        logger.info(
            "Agent %s executing task: %s",
            self.skill_name,
            task_description[:60],
        )

        result = self.executor.execute_task(
            task_description=task_description,
            skill_name=self.skill_name,
            operation_type=self._infer_operation_type(task_description),
        )

        output_preview = result.output[:100] if result.output else "no output"
        self.message_history.append(
            {
                "role": "assistant",
                "content": f"Executed: {task_description[:100]} -> {output_preview}",
            }
        )

        return result

    def reset_history(self) -> None:
        """Clear message history (AgentVerse protocol)."""
        self.message_history = []

    def get_allowed_tools(self) -> list[str]:
        """Return tools allowed for this agent's role.

        Returns
        -------
        list[str]
            List of tool names the agent may use
        """
        tools, _ = _ROLE_TOOLS.get(self.role, _ROLE_TOOLS["implementer"])
        return tools

    def get_disallowed_tools(self) -> list[str]:
        """Return tools disallowed for this agent's role.

        Returns
        -------
        list[str]
            List of tool names the agent may NOT use
        """
        _, disallowed = _ROLE_TOOLS.get(self.role, _ROLE_TOOLS["implementer"])
        return disallowed

    def select_model(self) -> str:
        """Select appropriate Ollama model based on skill tags.

        Returns
        -------
        str
            Model name for this skill (e.g., "qwen3-coder:30b")
        """
        skill_lower = self.skill_name.lower()

        if "code" in skill_lower or "python" in skill_lower or "implement" in skill_lower:
            return "qwen3-coder:30b"
        if "test" in skill_lower or "verify" in skill_lower or "lint" in skill_lower:
            return "phi3:mini"
        if "research" in skill_lower or "analyze" in skill_lower or "architect" in skill_lower:
            return "deepseek-r1:70b"

        return "qwen3-coder:30b"

    def _infer_operation_type(self, task_description: str) -> str:
        """Infer operation type from task description.

        Parameters
        ----------
        task_description : str
            Task description to analyze

        Returns
        -------
        str
            Operation type: generate, analyze, search, transform, persist
        """
        desc_lower = task_description.lower()

        if any(kw in desc_lower for kw in ["write", "create", "implement", "add", "new"]):
            return "generate"
        if any(kw in desc_lower for kw in ["analyze", "examine", "review", "check"]):
            return "analyze"
        if any(kw in desc_lower for kw in ["find", "search", "locate", "get"]):
            return "search"
        if any(kw in desc_lower for kw in ["transform", "convert", "modify", "change"]):
            return "transform"
        if any(kw in desc_lower for kw in ["save", "store", "persist", "log"]):
            return "persist"

        return "generate"
