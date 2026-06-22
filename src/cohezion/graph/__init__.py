"""Graph execution engine for DAG-native multi-agent workflows.

Inspired by MASFactory's graph-centric composition model, adapted for
Cohezion's compound engineering stack with SurrealDB persistence.
"""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.graph.builder import WorkflowBuilder as WorkflowBuilder

with contextlib.suppress(Exception):
    from cohezion.graph.engine import WorkflowEngine as WorkflowEngine

with contextlib.suppress(Exception):
    from cohezion.graph.nodes import AgentNode as AgentNode
    from cohezion.graph.nodes import CustomNode as CustomNode
    from cohezion.graph.nodes import LogicSwitchNode as LogicSwitchNode
    from cohezion.graph.nodes import ToolNode as ToolNode
    from cohezion.graph.nodes import WorkflowNode as WorkflowNode

with contextlib.suppress(Exception):
    from cohezion.graph.persistence import WorkflowPersistence as WorkflowPersistence

with contextlib.suppress(Exception):
    from cohezion.graph.types import EdgeSpec as EdgeSpec
    from cohezion.graph.types import NodeResult as NodeResult
    from cohezion.graph.types import NodeSpec as NodeSpec
    from cohezion.graph.types import NodeStatus as NodeStatus
    from cohezion.graph.types import WorkflowResult as WorkflowResult
    from cohezion.graph.types import WorkflowSpec as WorkflowSpec


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
