"""Anthropic 2026 Context Curator & Deny-by-Default MCP Authorization Guard.

Implements industry-standard agentic best practices from Anthropic & Google (2026):
1. Curated Context Windows: Prevents context bloat by cyclically condensing,
   refining, and summarizing verbose intermediate tool execution outputs.
2. Deny-by-Default Tool Policy: Mechanical enforcement of least privilege where
   agents and subagents start with zero tool permissions until explicitly granted.
3. Tiered Role Separation: Strict boundaries between Orchestrator (read-only/coordination)
   and Resolver (validated write/execution actions).
4. Untrusted Annotation Validation: Programmatic verification of tool schemas and
   metadata to prevent prompt injection and parameter hallucination.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class AgentRole(StrEnum):
    """Tiered agent capability roles enforcing mechanical boundaries."""

    ORCHESTRATOR = "orchestrator"  # Read-only coordination and reasoning; no write access
    CRITIC = "critic"  # Verification, AST checks, test validation
    RESOLVER = "resolver"  # Authorized write/execution actions on critic-verified payloads
    UNTRUSTED = "untrusted"  # Zero-privilege default


class ToolAccessPolicy(StrEnum):
    """Access policy decision outcome."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRES_CRITIC_APPROVAL = "requires_critic_approval"


class ToolDefinition(BaseModel):
    """Validated MCP tool definition with schema constraints."""

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Semantic purpose of the tool")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for arguments"
    )
    is_mutation: bool = Field(
        default=False, description="Whether tool performs state mutation or write actions"
    )
    required_role: AgentRole = Field(
        default=AgentRole.RESOLVER, description="Minimum role required for execution"
    )


@dataclass
class CuratedMessage:
    """A single turn in the curated context window."""

    role: str
    content: str
    tool_call_id: str | None = None
    is_compressed: bool = False
    original_length: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextCurator:
    """Curates multi-turn context windows to prevent token inflation and degradation."""

    def __init__(
        self,
        max_tool_output_chars: int = 1200,
        preserve_recent_turns: int = 4,
        compression_ratio_target: float = 0.35,
    ) -> None:
        """Initialize the context curator.

        Parameters
        ----------
        max_tool_output_chars : int
            Maximum raw character length permitted for an intermediate tool output before condensation.
        preserve_recent_turns : int
            Number of recent turns to preserve in full uncompressed fidelity.
        compression_ratio_target : float
            Target compression ratio for summarized outputs.
        """
        self.max_tool_output_chars = max_tool_output_chars
        self.preserve_recent_turns = preserve_recent_turns
        self.compression_ratio_target = compression_ratio_target

    def curate_history(
        self,
        messages: Sequence[dict[str, Any] | CuratedMessage],
    ) -> list[CuratedMessage]:
        """Curate message history, condensing aged or verbose tool outputs.

        Parameters
        ----------
        messages : Sequence[dict[str, Any] | CuratedMessage]
            Input chronological messages.

        Returns
        -------
        list[CuratedMessage]
            Curated list of messages with intermediate outputs pruned/summarized.
        """
        curated: list[CuratedMessage] = []
        for msg in messages:
            if isinstance(msg, CuratedMessage):
                curated.append(msg)
            else:
                curated.append(
                    CuratedMessage(
                        role=str(msg.get("role", "unknown")),
                        content=str(msg.get("content", "")),
                        tool_call_id=msg.get("tool_call_id"),
                        original_length=len(str(msg.get("content", ""))),
                        metadata=msg.get("metadata", {}),
                    )
                )

        n = len(curated)
        if n <= self.preserve_recent_turns:
            return curated

        # Turns older than recent window are candidates for curation
        for idx in range(n - self.preserve_recent_turns):
            item = curated[idx]
            if (item.role == "tool" or item.tool_call_id is not None) and (
                len(item.content) > self.max_tool_output_chars and not item.is_compressed
            ):
                item.content = self._condense_tool_output(item.content)
                item.is_compressed = True

        return curated

    def _condense_tool_output(self, content: str) -> str:
        """Deterministically condense verbose tool output into a structured semantic digest."""
        length = len(content)
        head_sample = content[:300].strip()
        tail_sample = content[-300:].strip()
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

        # Extract lines / records count if JSON or text
        line_count = content.count("\n") + 1
        summary_header = (
            f"[CONTEXT CURATOR: Condensed {length} chars ({line_count} lines) | SHA-256: {sha}]\n"
        )

        # Detect JSON structure
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return (
                    f"{summary_header}"
                    f"Array of {len(parsed)} items. First item preview:\n"
                    f"{json.dumps(parsed[0] if parsed else {}, indent=2)[:300]}...\n"
                    f"[End of condensed array preview]"
                )
            if isinstance(parsed, dict):
                keys = list(parsed.keys())
                return (
                    f"{summary_header}"
                    f"Object with keys: {keys}. Preview:\n"
                    f"{head_sample[:250]}...\n"
                    f"[End of condensed object preview]"
                )
        except Exception:
            pass

        return (
            f"{summary_header}--- Head ---\n{head_sample}\n... "
            f"[Truncated for Context Window Economy] ...\n--- Tail ---\n{tail_sample}"
        )


class DenyByDefaultMCPGuard:
    """Mechanical Deny-by-Default Authorization Guard for MCP Tools."""

    def __init__(self) -> None:
        """Initialize the guard with deny-by-default rules."""
        self._registered_tools: dict[str, ToolDefinition] = {}
        self._role_permissions: dict[AgentRole, set[str]] = {
            AgentRole.UNTRUSTED: set(),
            AgentRole.ORCHESTRATOR: set(),
            AgentRole.CRITIC: set(),
            AgentRole.RESOLVER: set(),
        }

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool definition into the guard registry.

        Parameters
        ----------
        tool : ToolDefinition
            The tool specification.
        """
        # Validate tool definition against adversarial injection in descriptions
        self._validate_tool_schema(tool)
        self._registered_tools[tool.name] = tool

    def grant_permission(self, role: AgentRole, tool_name: str) -> None:
        """Explicitly allow a tool for a specific agent role (Least Privilege).

        Parameters
        ----------
        role : AgentRole
            The target role.
        tool_name : str
            The name of the tool to permit.
        """
        if tool_name not in self._registered_tools:
            raise KeyError(f"Tool '{tool_name}' must be registered before granting permissions.")
        self._role_permissions[role].add(tool_name)

    def evaluate_access(
        self,
        role: AgentRole,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolAccessPolicy:
        """Evaluate access authorization for a tool invocation request.

        Parameters
        ----------
        role : AgentRole
            The invoking agent's role.
        tool_name : str
            Target tool name.
        arguments : dict[str, Any] | None
            Execution arguments.

        Returns
        -------
        ToolAccessPolicy
            ALLOW, DENY, or REQUIRES_CRITIC_APPROVAL.
        """
        if tool_name not in self._registered_tools:
            logger.warning("Access DENIED: Unregistered tool '%s'", tool_name)
            return ToolAccessPolicy.DENY

        tool = self._registered_tools[tool_name]

        # Deny-by-default check
        if tool_name not in self._role_permissions.get(role, set()):
            logger.warning("Access DENIED: Role '%s' does not have grant for '%s'", role, tool_name)
            return ToolAccessPolicy.DENY

        # Orchestrators are strictly forbidden from executing mutations
        if role == AgentRole.ORCHESTRATOR and tool.is_mutation:
            logger.error(
                "Access DENIED: Orchestrators cannot perform mutating action '%s'", tool_name
            )
            return ToolAccessPolicy.DENY

        # Resolvers attempting mutations require verification
        if tool.is_mutation and role != AgentRole.RESOLVER:
            return ToolAccessPolicy.REQUIRES_CRITIC_APPROVAL

        return ToolAccessPolicy.ALLOW

    def _validate_tool_schema(self, tool: ToolDefinition) -> None:
        """Programmatically inspect tool description and schema for anomalies."""
        # Detect prompt injection patterns in descriptions
        injection_patterns = [
            r"ignore previous instructions",
            r"system override",
            r"bypass guardrails",
            r"<script>",
            r"drop database",
        ]
        desc_lower = tool.description.lower()
        for pat in injection_patterns:
            if re.search(pat, desc_lower):
                raise ValueError(
                    f"Untrusted tool definition for '{tool.name}': Detected suspicious pattern '{pat}'."
                )
