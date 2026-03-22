"""Graph execution engine for DAG-native multi-agent workflows.

Inspired by MASFactory's graph-centric composition model, adapted for
Cohezion's compound engineering stack with SurrealDB persistence.
"""

from cohezion.graph.builder import WorkflowBuilder
from cohezion.graph.engine import WorkflowEngine
from cohezion.graph.nodes import (
    AgentNode,
    CustomNode,
    LogicSwitchNode,
    ToolNode,
    WorkflowNode,
)
from cohezion.graph.persistence import WorkflowPersistence
from cohezion.graph.types import (
    EdgeSpec,
    NodeResult,
    NodeSpec,
    NodeStatus,
    WorkflowResult,
    WorkflowSpec,
)


__all__ = [
    "AgentNode",
    "CustomNode",
    "EdgeSpec",
    "LogicSwitchNode",
    "NodeResult",
    "NodeSpec",
    "NodeStatus",
    "ToolNode",
    "WorkflowBuilder",
    "WorkflowEngine",
    "WorkflowNode",
    "WorkflowPersistence",
    "WorkflowResult",
    "WorkflowSpec",
]
