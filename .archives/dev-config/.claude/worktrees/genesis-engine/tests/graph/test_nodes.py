"""Tests for workflow node implementations."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cohezion.graph.nodes import (
    AgentNode,
    CustomNode,
    LogicSwitchNode,
    ToolNode,
    WorkflowNode,
)
from cohezion.graph.types import NodeSpec


class TestWorkflowNodeABC:
    def test_cannot_instantiate_abstract(self):
        spec = NodeSpec(id="n1", name="test", node_type="agent", pull_keys=[], push_keys=[])
        with pytest.raises(TypeError):
            WorkflowNode(spec)  # type: ignore[abstract]


class TestAgentNode:
    @pytest.fixture
    def agent_spec(self):
        return NodeSpec(
            id="agent-1",
            name="researcher",
            node_type="agent",
            pull_keys=["query"],
            push_keys=["findings"],
            attributes={"task_description": "Research topic X"},
        )

    def test_create_agent_node(self, agent_spec):
        node = AgentNode(agent_spec)
        assert node.spec.id == "agent-1"
        assert node.spec.node_type == "agent"

    @pytest.mark.asyncio
    async def test_forward_with_execute_fn(self, agent_spec):
        node = AgentNode(agent_spec)

        async def mock_execute(inputs: dict) -> dict:
            return {"findings": f"Results for: {inputs.get('query', '')}"}

        node.set_execute_fn(mock_execute)
        result = await node.forward({"query": "quantum computing"})
        assert result["findings"] == "Results for: quantum computing"

    @pytest.mark.asyncio
    async def test_forward_without_execute_fn_returns_passthrough(self, agent_spec):
        node = AgentNode(agent_spec)
        result = await node.forward({"query": "test"})
        assert result == {"query": "test"}


class TestToolNode:
    @pytest.fixture
    def tool_spec(self):
        return NodeSpec(
            id="tool-1",
            name="web_search",
            node_type="tool",
            pull_keys=["query"],
            push_keys=["results"],
            attributes={"tool_name": "web_search"},
        )

    @pytest.mark.asyncio
    async def test_forward_calls_tool(self, tool_spec):
        tool_fn = AsyncMock(return_value={"results": ["page1", "page2"]})
        node = ToolNode(tool_spec, tool_fn=tool_fn)
        result = await node.forward({"query": "AI papers"})
        tool_fn.assert_awaited_once_with({"query": "AI papers"})
        assert result["results"] == ["page1", "page2"]

    @pytest.mark.asyncio
    async def test_forward_without_tool_fn_passes_through(self, tool_spec):
        node = ToolNode(tool_spec)
        result = await node.forward({"query": "test"})
        assert result == {"query": "test"}


class TestLogicSwitchNode:
    @pytest.fixture
    def switch_spec(self):
        return NodeSpec(
            id="switch-1",
            name="quality_gate",
            node_type="logic_switch",
            pull_keys=["score"],
            push_keys=["route"],
        )

    @pytest.mark.asyncio
    async def test_routes_based_on_condition(self, switch_spec):
        def condition_fn(inputs: dict) -> str:
            return "approve" if inputs.get("score", 0) >= 0.8 else "reject"

        node = LogicSwitchNode(switch_spec, condition_fn=condition_fn)

        result = await node.forward({"score": 0.9})
        assert result["route"] == "approve"

        result = await node.forward({"score": 0.3})
        assert result["route"] == "reject"

    @pytest.mark.asyncio
    async def test_default_route_without_condition(self, switch_spec):
        node = LogicSwitchNode(switch_spec)
        result = await node.forward({"score": 0.5})
        assert result["route"] == "default"


class TestCustomNode:
    @pytest.mark.asyncio
    async def test_custom_forward(self):
        spec = NodeSpec(
            id="custom-1",
            name="transform",
            node_type="custom",
            pull_keys=["data"],
            push_keys=["transformed"],
        )

        async def transform(inputs: dict) -> dict:
            return {"transformed": [x * 2 for x in inputs.get("data", [])]}

        node = CustomNode(spec, forward_fn=transform)
        result = await node.forward({"data": [1, 2, 3]})
        assert result["transformed"] == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_custom_without_fn_passes_through(self):
        spec = NodeSpec(id="c1", name="noop", node_type="custom", pull_keys=[], push_keys=[])
        node = CustomNode(spec)
        result = await node.forward({"x": 1})
        assert result == {"x": 1}
