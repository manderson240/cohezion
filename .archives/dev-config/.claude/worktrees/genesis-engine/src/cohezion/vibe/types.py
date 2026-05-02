"""Vibe Graphing types — NL intent to structured workflow specification.

VibeIntent captures extracted intent from natural language text.
VibeWorkflowSpec describes the workflow before compilation to a WorkflowSpec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class OperationType(StrEnum):
    """High-level operation type inferred from NL text."""

    RESEARCH = "research"
    IMPLEMENT = "implement"
    ANALYZE = "analyze"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    ORCHESTRATE = "orchestrate"
    UNKNOWN = "unknown"


@dataclass
class VibeIntent:
    """Structured intent extracted from natural language text.

    Attributes:
        raw_text: Original NL input.
        keywords: Extracted signal words (nouns, verbs, domain terms).
        operation_type: High-level operation category.
        complexity: Estimated workflow size (1-5 scale).
        confidence: Parser confidence in this interpretation (0.0-1.0).
        sub_intents: Optional decomposed sub-goals for complex requests.
    """

    raw_text: str
    keywords: list[str]
    operation_type: OperationType
    complexity: int  # 1 (trivial) to 5 (highly complex)
    confidence: float  # 0.0 to 1.0
    sub_intents: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.complexity <= 5:
            raise ValueError(f"complexity must be 1-5, got {self.complexity}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")


@dataclass
class NodeDescription:
    """Human-readable description of a workflow node before compilation.

    Attributes:
        name: Proposed node name.
        role: What this node does in the workflow.
        agent_role: Role string for agent matching (e.g. "researcher", "coder").
        inputs: Expected input keys from prior nodes.
        outputs: Keys this node will produce.
    """

    name: str
    role: str
    agent_role: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


@dataclass
class EdgeDescription:
    """Human-readable edge description before compilation.

    Attributes:
        from_name: Source node name.
        to_name: Target node name.
        keys: Data keys flowing across this edge.
        condition: Optional routing condition expression.
    """

    from_name: str
    to_name: str
    keys: list[str] = field(default_factory=list)
    condition: str | None = None


@dataclass
class VibeWorkflowSpec:
    """Intermediate workflow description produced by VibeSpecifier.

    This is the bridge between VibeIntent (NL) and WorkflowSpec (graph).

    Attributes:
        intent: The originating VibeIntent.
        node_descriptions: Ordered list of proposed workflow nodes.
        edge_descriptions: Proposed edges between nodes.
        parameters: Additional workflow-level parameters.
        similar_past_workflows: IDs of similar past workflows from vault search.
        template_used: Name of the vault template applied, if any.
    """

    intent: VibeIntent
    node_descriptions: list[NodeDescription]
    edge_descriptions: list[EdgeDescription]
    parameters: dict[str, Any] = field(default_factory=dict)
    similar_past_workflows: list[str] = field(default_factory=list)
    template_used: str | None = None

    @property
    def node_count(self) -> int:
        return len(self.node_descriptions)

    @property
    def edge_count(self) -> int:
        return len(self.edge_descriptions)
