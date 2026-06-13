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

    from cohezion.compound.context_policy import ContextBudget
    from cohezion.flux.aggregator import FluxAggregator
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

    When a ``flux_aggregator`` is provided, the node queries FLUX with a
    role-scoped query before execution, injecting targeted context blocks
    into the inputs under the ``_flux_context`` key.
    """

    # Max context blocks per node — fewer targeted blocks > many generic ones
    _FLUX_TOP_K = 3
    # Minimum relevance score — blocks below this are noise, not signal
    _FLUX_MIN_RELEVANCE = 0.5

    def __init__(
        self,
        spec: NodeSpec,
        flux_aggregator: FluxAggregator | None = None,
        context_budget: ContextBudget | None = None,
    ) -> None:
        super().__init__(spec)
        self._execute_fn: Callable[..., Any] | None = None
        self._flux = flux_aggregator
        self._budget = context_budget

    def set_execute_fn(self, fn: Callable[..., Any]) -> None:
        """Set the async callable that performs agent execution."""
        self._execute_fn = fn

    async def forward(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if self._execute_fn is None:
            return inputs

        enriched = dict(inputs)
        if self._flux is not None:
            context_strings = await self._get_flux_context(inputs)
            if context_strings:
                enriched["_flux_context"] = context_strings

        result = await self._execute_fn(enriched)
        output = result if isinstance(result, dict) else {"output": result}
        output.pop("_flux_context", None)  # Don't propagate internal context downstream
        return output

    async def _get_flux_context(self, inputs: dict[str, Any]) -> list[str]:
        """Query FLUX with a node-scoped query. Non-blocking on failure.

        Uses ContextBudget parameters when available, otherwise falls
        back to class-level defaults. Only injects blocks above the
        relevance threshold — zero tokens is better than noise tokens.
        """
        try:
            top_k = self._budget.flux_top_k if self._budget else self._FLUX_TOP_K
            min_rel = self._budget.flux_min_relevance if self._budget else self._FLUX_MIN_RELEVANCE
            sources = (
                list(self._budget.flux_sources)
                if self._budget and self._budget.flux_sources
                else None
            )

            query = self._build_context_query(inputs)
            kwargs: dict = {"top_k": top_k}
            if sources is not None:
                kwargs["sources"] = sources
            ctx = await self._flux.get_context(query, **kwargs)  # type: ignore[union-attr]
            return [block.content for block in ctx.blocks if block.relevance_score >= min_rel]
        except Exception:
            logger.debug("FLUX context injection failed for node '%s' (non-blocking)", self.spec.id)
            return []

    def _build_context_query(self, inputs: dict[str, Any]) -> str:
        """Build a FLUX query scoped to this node's role and runtime data."""
        parts: list[str] = []

        # Primary: node description or name (structural scope)
        desc = self.spec.attributes.get("description", "")
        if desc:
            parts.append(desc)
        else:
            parts.append(self.spec.name)

        # Secondary: string input values (runtime scope, capped for token efficiency)
        for value in inputs.values():
            if isinstance(value, str) and len(value) > 3:
                parts.append(value)
                if len(parts) >= 3:
                    break

        return " ".join(parts)


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
