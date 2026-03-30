"""Tests for cohezion.protocols.a2a_server — A2A protocol server and client.

Phase 3c coverage push.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.protocols.a2a_server import (
    A2AClient,
    A2AMessage,
    A2AServer,
    A2ATask,
    AgentCard,
    TaskState,
)


class TestTaskState:
    """Tests for TaskState enum."""

    def test_all_states_exist(self):
        """Should define all A2A lifecycle states."""
        assert TaskState.SUBMITTED == "submitted"
        assert TaskState.WORKING == "working"
        assert TaskState.INPUT_REQUIRED == "input-required"
        assert TaskState.COMPLETED == "completed"
        assert TaskState.CANCELED == "canceled"
        assert TaskState.FAILED == "failed"

    def test_state_count(self):
        """Should have exactly 6 states."""
        assert len(TaskState) == 6


class TestAgentCard:
    """Tests for AgentCard dataclass and serialization."""

    def test_default_card(self):
        """Should create card with sensible defaults."""
        card = AgentCard()
        assert card.name == "Cohezion Agent"
        assert card.version == "1.0.2"
        assert len(card.capabilities) == 4

    def test_to_dict_structure(self):
        """Should serialize with A2A-compliant structure."""
        card = AgentCard()
        d = card.to_dict()
        assert "name" in d
        assert "capabilities" in d
        assert d["capabilities"]["streaming"] is True
        assert "skills" in d
        assert "authentication" in d
        assert "defaultInputModes" in d
        assert "defaultOutputModes" in d

    def test_to_json(self):
        """Should serialize to valid JSON string."""
        card = AgentCard()
        json_str = card.to_json()
        import json
        parsed = json.loads(json_str)
        assert parsed["name"] == "Cohezion Agent"

    def test_custom_card(self):
        """Should accept custom parameters."""
        card = AgentCard(name="TestAgent", version="2.0.0", url="http://test:8080")
        d = card.to_dict()
        assert d["name"] == "TestAgent"
        assert d["version"] == "2.0.0"
        assert d["url"] == "http://test:8080"

    def test_skills_in_dict(self):
        """Should map capabilities to skills format."""
        card = AgentCard(capabilities=["analysis", "routing"])
        d = card.to_dict()
        assert len(d["skills"]) == 2
        assert d["skills"][0]["id"] == "analysis"


class TestA2AServer:
    """Tests for A2AServer task lifecycle."""

    @pytest.fixture()
    def server(self):
        """Create a default A2A server."""
        return A2AServer()

    def test_get_agent_card(self, server):
        """Should return the agent card dict."""
        card = server.get_agent_card()
        assert card["name"] == "Cohezion Agent"

    @pytest.mark.asyncio
    async def test_send_task_creates_new(self, server):
        """Should create a new task with COMPLETED state."""
        with patch.object(server, "_route_to_agent", new_callable=AsyncMock, return_value="done"):
            task = await server.send_task(
                {"role": "user", "parts": [{"type": "text", "text": "hello"}]}
            )
        assert isinstance(task, A2ATask)
        assert task.state == TaskState.COMPLETED
        assert len(task.messages) == 2  # user msg + agent response

    @pytest.mark.asyncio
    async def test_send_task_continues_existing(self, server):
        """Should continue an existing task."""
        with patch.object(server, "_route_to_agent", new_callable=AsyncMock, return_value="r1"):
            t1 = await server.send_task(
                {"role": "user", "parts": [{"type": "text", "text": "first"}]}
            )
        with patch.object(server, "_route_to_agent", new_callable=AsyncMock, return_value="r2"):
            t2 = await server.send_task(
                {"role": "user", "parts": [{"type": "text", "text": "second"}]},
                task_id=t1.id,
            )
        assert t2.id == t1.id
        assert len(t2.messages) == 4  # 2 user + 2 agent

    @pytest.mark.asyncio
    async def test_send_task_failure(self, server):
        """Should set FAILED state on routing error."""
        with patch.object(
            server, "_route_to_agent", new_callable=AsyncMock, side_effect=RuntimeError("boom")
        ):
            task = await server.send_task(
                {"role": "user", "parts": [{"type": "text", "text": "fail"}]}
            )
        assert task.state == TaskState.FAILED
        assert "Error" in task.messages[-1].parts[0]["text"]

    @pytest.mark.asyncio
    async def test_get_task_exists(self, server):
        """Should retrieve existing task."""
        with patch.object(server, "_route_to_agent", new_callable=AsyncMock, return_value="ok"):
            created = await server.send_task(
                {"role": "user", "parts": [{"type": "text", "text": "test"}]}
            )
        fetched = await server.get_task(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, server):
        """Should return None for unknown task."""
        result = await server.get_task("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_working_task(self, server):
        """Should cancel a working task."""
        task = A2ATask(id="cancel-me", state=TaskState.WORKING)
        server.tasks["cancel-me"] = task
        result = await server.cancel_task("cancel-me")
        assert result is True
        assert task.state == TaskState.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_completed_task_fails(self, server):
        """Should not cancel already completed tasks."""
        task = A2ATask(id="done-task", state=TaskState.COMPLETED)
        server.tasks["done-task"] = task
        result = await server.cancel_task("done-task")
        assert result is False
        assert task.state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, server):
        """Should return False for unknown task."""
        result = await server.cancel_task("nope")
        assert result is False

    @pytest.mark.asyncio
    async def test_route_empty_message(self, server):
        """Should handle task with no user messages."""
        task = A2ATask(id="empty", state=TaskState.WORKING, messages=[])
        result = await server._route_to_agent(task)
        assert result == "No user message found in task."

    @pytest.mark.asyncio
    async def test_route_empty_prompt(self, server):
        """Should handle task with empty text parts."""
        task = A2ATask(
            id="blank",
            state=TaskState.WORKING,
            messages=[A2AMessage(role="user", parts=[{"type": "text", "text": "   "}])],
        )
        result = await server._route_to_agent(task)
        assert result == "Empty prompt received."


class TestA2AClient:
    """Tests for A2AClient."""

    def test_init_defaults(self):
        """Should initialize with default timeout."""
        client = A2AClient()
        assert client.timeout == 30.0

    def test_init_custom_timeout(self):
        """Should accept custom timeout."""
        client = A2AClient(timeout=60.0)
        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_discover_agent_success(self):
        """Should discover agent via well-known endpoint."""
        mock_card = {"name": "Remote Agent", "version": "1.0"}
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = mock_card

        client = A2AClient()
        with patch("httpx.AsyncClient") as mock_http:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_http.return_value = mock_instance

            result = await client.discover_agent("http://localhost:9000")
        assert result == mock_card
        assert "http://localhost:9000" in client._discovered_agents

    @pytest.mark.asyncio
    async def test_discover_agent_failure(self):
        """Should return None on discovery failure."""
        client = A2AClient()
        with patch("httpx.AsyncClient") as mock_http:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=ConnectionError("refused"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_http.return_value = mock_instance

            result = await client.discover_agent("http://dead:9000")
        assert result is None
