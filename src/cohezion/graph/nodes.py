"""Workflow node implementations for the graph execution engine.

Each node type wraps a different execution pattern:
- AgentNode: LLM agent via CompoundExecutor
- ToolNode: MCP tool call
- LogicSwitchNode: Conditional routing
- CustomNode: User-defined async callable
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable

    from cohezion.graph.types import NodeSpec


logger = logging.getLogger(__name__)


class WorkflowNode(ABC):
    """Abstract base for all workflow nodes.

    Subclasses implement ``forward()`` to define execution behavior.
    The engine calls ``forward(inputs)`` with data gathered from incoming edges.
    """

    def __init__(self, spec: NodeSpec) -> None:
        self.spec = spec

    @abstractmethod
    async def forward(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute node logic and return output data."""


class AgentNode(WorkflowNode):
    """Node wrapping an LLM agent execution.

    By default passes inputs through. Set an execute function via
    ``set_execute_fn()`` to wire up CompoundExecutor or any async callable.
    """

    def __init__(self, spec: NodeSpec) -> None:
        super().__init__(spec)
        self._execute_fn: Callable[..., Any] | None = None

    def set_execute_fn(self, fn: Callable[..., Any]) -> None:
        """Set the async callable that performs agent execution."""
        self._execute_fn = fn

    async def forward(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if self._execute_fn is None:
            return inputs
        result = await self._execute_fn(inputs)
        return result if isinstance(result, dict) else {"output": result}


class ToolNode(WorkflowNode):
    """Node wrapping an MCP tool call or any async tool function."""

    def __init__(
        self,
        spec: NodeSpec,
        tool_fn: Callable[..., Any] | None = None,
    ) -> None:
        super().__init__(spec)
        self._tool_fn = tool_fn

    async def forward(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if self._tool_fn is None:
            return inputs
        result = await self._tool_fn(inputs)
        return result if isinstance(result, dict) else {"output": result}


class LogicSwitchNode(WorkflowNode):
    """Conditional routing node.

    Evaluates a condition function against inputs and returns a route key.
    The engine uses the route key to select which outgoing edge to activate.
    """

    def __init__(
        self,
        spec: NodeSpec,
        condition_fn: Callable[[dict[str, Any]], str] | None = None,
    ) -> None:
        super().__init__(spec)
        self._condition_fn = condition_fn

    async def forward(self, inputs: dict[str, Any]) -> dict[str, Any]:
        route_key = self.spec.push_keys[0] if self.spec.push_keys else "route"
        if self._condition_fn is None:
            return {route_key: "default"}
        route = self._condition_fn(inputs)
        return {route_key: route}


class CustomNode(WorkflowNode):
    """Node with user-defined async forward logic."""

    def __init__(
        self,
        spec: NodeSpec,
        forward_fn: Callable[..., Any] | None = None,
    ) -> None:
        super().__init__(spec)
        self._forward_fn = forward_fn

    async def forward(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if self._forward_fn is None:
            return inputs
        result = await self._forward_fn(inputs)
        return result if isinstance(result, dict) else {"output": result}
