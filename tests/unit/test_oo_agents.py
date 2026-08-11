"""Unit tests for Object-Oriented Agents (labs-OO-Agents) module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from cohezion.swarm.oo_agents import BaseOOAgent, capability, dynamic, OOAgentState


class CustomOOAgent(BaseOOAgent):
    """Test OO Agent implementation."""

    def __init__(self, agent_id: str = "test-agent") -> None:
        super().__init__(agent_id=agent_id, role="Test Specialist")

    @capability(name="calculate_hash", description="Calculates deterministic hash")
    def calculate_hash(self, value: str) -> str:
        """Deterministic Python method (0 ms latency)."""
        return f"hash_{value}"

    @dynamic
    async def synthesize_code(self, spec: str) -> str:
        """Synthesizes code dynamically based on spec."""
        ...


def test_oo_agent_state_initialization():
    agent = CustomOOAgent(agent_id="agent-001")
    assert agent.state.agent_id == "agent-001"
    assert agent.state.role == "Test Specialist"
    assert len(agent.state.state_vector) == 12


def test_oo_agent_get_capabilities():
    agent = CustomOOAgent()
    caps = agent.get_capabilities()

    assert "calculate_hash" in caps
    assert caps["calculate_hash"]["name"] == "calculate_hash"
    assert caps["calculate_hash"]["is_dynamic"] is False

    assert "synthesize_code" in caps
    assert caps["synthesize_code"]["is_dynamic"] is True


def test_oo_agent_deterministic_method():
    agent = CustomOOAgent()
    res = agent.calculate_hash("hello")
    assert res == "hash_hello"


@pytest.mark.asyncio
async def test_oo_agent_execute_dynamic_capability():
    agent = CustomOOAgent()

    mock_resp = MagicMock()
    mock_resp.content = "def foo(): return 42"

    with patch.object(
        agent.router, "route_by_capability", new_callable=AsyncMock, return_value=mock_resp
    ) as mock_route, patch.object(
        agent.event_bus, "publish", new_callable=AsyncMock
    ) as mock_publish:
        result = await agent.execute_dynamic_capability("synthesize_code", spec="build function")

        assert result == "def foo(): return 42"
        mock_route.assert_called_once()
        mock_publish.assert_called_once()
