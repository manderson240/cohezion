"""Tests for ContextEngineeringInfrastructure MCP integration.

Tests cover:
- MCP tool registration and execution
- Compound operations (log_decision, log_experiment,
  extract_pattern, find_relevant_context)
- Backward compatibility (works without MCP configured)
- Configuration loading and error handling
- Integration with RetrospectionEngine, SkillRefiner, JourneyPersistence
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.core.context_engineering import ContextEngineeringInfrastructure
from cohezion.core.mcp_client import (
    MCPAuthenticationError,
    MCPClient,
    MCPConfig,
    MCPConnectionError,
    MCPToolError,
)


def _make_sse_text(data: dict) -> str:
    """Create SSE-formatted response text from a dict."""
    return f"event: message\ndata: {json.dumps(data)}\n\n"


def _make_init_response(mock_client):
    """Configure mock AsyncClient for successful session initialization."""
    init_response = MagicMock()
    init_response.status_code = 200
    init_response.headers = {"mcp-session-id": "test-session-123"}
    init_response.text = _make_sse_text(
        {"jsonrpc": "2.0", "id": 0, "result": {"protocolVersion": "2024-11-05"}}
    )
    init_response.raise_for_status = MagicMock()
    # AsyncClient.post is a coroutine; AsyncMock makes it awaitable
    mock_client.post = AsyncMock(return_value=init_response)
    mock_client.aclose = AsyncMock()
    return init_response


class TestMCPClient(unittest.TestCase):
    """Test MCP client connectivity and tool calls."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = MCPConfig(
            server_url="http://localhost:8360", api_key="test-api-key", timeout=5.0
        )

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_connect_success(self, mock_client_class):
        """Test successful connection to MCP server."""
        mock_client = MagicMock()
        _make_init_response(mock_client)
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)
        asyncio.run(client.connect())

        # Verify session was initialized via POST /mcp
        mock_client_class.assert_called_once()
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertEqual(call_args[0][0], "/mcp")

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_connect_authentication_failure(self, mock_client_class):
        """Test authentication failure on connect."""
        import httpx

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403

        http_error = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response,
        )
        mock_response.raise_for_status.side_effect = http_error
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)

        with self.assertRaises(MCPAuthenticationError):
            asyncio.run(client.connect())

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_connect_connection_failure(self, mock_client_class):
        """Test connection failure when server is unreachable."""
        import httpx

        mock_client = MagicMock()
        request_error = httpx.RequestError("Connection refused", request=MagicMock())
        mock_client.post = AsyncMock(side_effect=request_error)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)

        with self.assertRaises(MCPConnectionError):
            asyncio.run(client.connect())

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_call_tool_success(self, mock_client_class):
        """Test successful tool call."""
        mock_client = MagicMock()
        _make_init_response(mock_client)
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)
        asyncio.run(client.connect())

        # Now set up tool call response
        tool_response = MagicMock()
        tool_response.status_code = 200
        tool_response.raise_for_status = MagicMock()
        tool_response.text = _make_sse_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "Tool executed successfully"}]},
            }
        )
        mock_client.post = AsyncMock(return_value=tool_response)

        result = asyncio.run(client._call_tool("test_tool", {"arg": "value"}))
        self.assertEqual(result, "Tool executed successfully")

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_call_tool_error_response(self, mock_client_class):
        """Test tool call with error response."""
        mock_client = MagicMock()
        _make_init_response(mock_client)
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)
        asyncio.run(client.connect())

        # Set up error response
        tool_response = MagicMock()
        tool_response.status_code = 200
        tool_response.raise_for_status = MagicMock()
        tool_response.text = _make_sse_text(
            {"jsonrpc": "2.0", "id": 1, "error": {"message": "Tool execution failed"}}
        )
        mock_client.post = AsyncMock(return_value=tool_response)

        with self.assertRaises(MCPToolError):
            asyncio.run(client._call_tool("test_tool", {"arg": "value"}))

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_vault_operations(self, mock_client_class):
        """Test basic vault operations."""
        mock_client = MagicMock()
        _make_init_response(mock_client)
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)
        asyncio.run(client.connect())

        # Set up tool response
        tool_response = MagicMock()
        tool_response.status_code = 200
        tool_response.raise_for_status = MagicMock()
        tool_response.text = _make_sse_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "Operation successful"}]},
            }
        )
        mock_client.post = AsyncMock(return_value=tool_response)

        self.assertEqual(asyncio.run(client.vault_read("test.md")), "Operation successful")
        self.assertEqual(
            asyncio.run(client.vault_write("test.md", "content")),
            "Operation successful",
        )
        self.assertEqual(asyncio.run(client.vault_delete("test.md")), "Operation successful")

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_compound_operations(self, mock_client_class):
        """Test compound operations (decisions, experiments, patterns)."""
        mock_client = MagicMock()
        _make_init_response(mock_client)
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)
        asyncio.run(client.connect())

        # Test log_decision
        tool_response = MagicMock()
        tool_response.status_code = 200
        tool_response.raise_for_status = MagicMock()
        tool_response.text = _make_sse_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "content": [{"type": "text", "text": "decisions/2025-01-15-test-decision.md"}]
                },
            }
        )
        mock_client.post = AsyncMock(return_value=tool_response)

        result = asyncio.run(
            client.vault_log_decision(
                project="test",
                title="Test Decision",
                context="Test context",
                decision="Test decision",
                rationale="Test rationale",
            )
        )
        self.assertIn("decisions/", result)

        # Test log_experiment
        tool_response.text = _make_sse_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "content": [
                        {"type": "text", "text": "experiments/2025-01-15-test-experiment.md"}
                    ]
                },
            }
        )
        result = asyncio.run(
            client.vault_log_experiment(
                project="test",
                hypothesis="Test hypothesis",
                method="Test method",
                result="Test result",
            )
        )
        self.assertIn("experiments/", result)

        # Test extract_pattern
        tool_response.text = _make_sse_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "patterns/test-pattern.md"}]},
            }
        )
        result = asyncio.run(
            client.vault_extract_pattern(
                source_path="test.md",
                pattern_name="Test Pattern",
                description="Test description",
            )
        )
        self.assertIn("patterns/", result)

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_find_relevant_context(self, mock_client_class):
        """Test find_relevant_context compound operation."""
        mock_client = MagicMock()
        _make_init_response(mock_client)
        mock_client_class.return_value = mock_client

        client = MCPClient(self.config)
        asyncio.run(client.connect())

        # Set up context search response
        tool_response = MagicMock()
        tool_response.status_code = 200
        tool_response.raise_for_status = MagicMock()
        context_json = json.dumps(
            [{"path": "decisions/test.md", "category": "decision", "match_count": 3}]
        )
        tool_response.text = _make_sse_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": context_json}]},
            }
        )
        mock_client.post = AsyncMock(return_value=tool_response)

        result = asyncio.run(client.vault_find_relevant_context("test query"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["category"], "decision")
        self.assertEqual(result[0]["match_count"], 3)


class TestContextEngineeringInfrastructure(unittest.TestCase):
    """Test ContextEngineeringInfrastructure with MCP integration."""

    def test_backward_compatibility_no_mcp(self):
        """Test infrastructure works without MCP configured (backward compatible)."""
        # Create infrastructure without MCP credentials
        cei = ContextEngineeringInfrastructure()

        # Should not have MCP enabled
        self.assertFalse(cei.is_mcp_enabled())

        # Should still support custom tool registration
        cei.register_tool("custom_tool", lambda x: x * 2)
        self.assertEqual(cei.list_tools(), ["custom_tool"])
        self.assertEqual(cei.execute_tool("custom_tool", x=5), 10)

    def test_backward_compatibility_mcp_disabled(self):
        """Test infrastructure with MCP explicitly disabled."""
        # Create infrastructure with MCP disabled
        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=False,
        )

        # Should not have MCP enabled
        self.assertFalse(cei.is_mcp_enabled())

        # Should not have MCP tools registered
        self.assertEqual(cei.list_tools(), [])

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_mcp_initialization_success(self, mock_create_client):
        """Test successful MCP initialization."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Should have MCP enabled
        self.assertTrue(cei.is_mcp_enabled())

        # Should have registered compound operations
        tools = cei.list_tools()
        self.assertIn("log_decision", tools)
        self.assertIn("log_experiment", tools)
        self.assertIn("extract_pattern", tools)
        self.assertIn("find_relevant_context", tools)

        # Verify client connection was called
        mock_client.connect.assert_called_once()

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_mcp_initialization_failure_graceful_degradation(self, mock_create_client):
        """Test graceful degradation when MCP initialization fails."""
        # Simulate connection failure
        mock_client = MagicMock()
        mock_client.connect.side_effect = MCPConnectionError("Connection failed")
        mock_create_client.return_value = mock_client

        # Should not raise exception, but log warning
        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Should not have MCP enabled after failure
        self.assertFalse(cei.is_mcp_enabled())

        # Should still work as local-only infrastructure
        cei.register_tool("local_tool", lambda x: x + 1)
        self.assertEqual(cei.execute_tool("local_tool", x=5), 6)

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_execute_compound_operations(self, mock_create_client):
        """Test executing compound operations via infrastructure."""
        mock_client = MagicMock()
        mock_client.vault_log_decision.return_value = "decisions/2025-01-15-test.md"
        mock_client.vault_log_experiment.return_value = "experiments/2025-01-15-test.md"
        mock_client.vault_extract_pattern.return_value = "patterns/test-pattern.md"
        mock_client.vault_find_relevant_context.return_value = [
            {"path": "test.md", "category": "decision", "match_count": 2}
        ]
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Test log_decision
        result = cei.execute_tool(
            "log_decision",
            project="test",
            title="Test Decision",
            context="Context",
            decision="Decision",
            rationale="Rationale",
        )
        self.assertIn("decisions/", result)

        # Test log_experiment
        result = cei.execute_tool(
            "log_experiment",
            project="test",
            hypothesis="Hypothesis",
            method="Method",
            result="Result",
        )
        self.assertIn("experiments/", result)

        # Test extract_pattern
        result = cei.execute_tool(
            "extract_pattern",
            source_path="test.md",
            pattern_name="Pattern",
            description="Description",
        )
        self.assertIn("patterns/", result)

        # Test find_relevant_context
        result = cei.execute_tool("find_relevant_context", query="test")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_mixed_tools_local_and_mcp(self, mock_create_client):
        """Test infrastructure with both local and MCP tools."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Register local tool
        cei.register_tool("local_tool", lambda x: x * 3)

        # Should have both MCP and local tools
        tools = cei.list_tools()
        self.assertIn("log_decision", tools)
        self.assertIn("local_tool", tools)

        # Should be able to execute both
        result = cei.execute_tool("local_tool", x=4)
        self.assertEqual(result, 12)

    def test_execute_nonexistent_tool_error(self):
        """Test executing a tool that doesn't exist raises error."""
        cei = ContextEngineeringInfrastructure()

        with self.assertRaises(ValueError) as ctx:
            cei.execute_tool("nonexistent_tool")

        self.assertIn("not found", str(ctx.exception))

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_close_cleans_up_mcp_connection(self, mock_create_client):
        """Test close method cleans up MCP connection."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        self.assertTrue(cei.is_mcp_enabled())

        cei.close()

        # Should have closed MCP client
        mock_client.close.assert_called_once()

        # Should no longer have MCP enabled
        self.assertFalse(cei.is_mcp_enabled())

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_configuration_from_environment(self, mock_create_client):
        """Test loading MCP configuration from environment variables."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # In real usage, these would come from env vars or config file
        # Here we're testing the infrastructure accepts them as parameters
        ContextEngineeringInfrastructure(
            mcp_server_url="http://custom-server:8360",
            mcp_api_key="custom-api-key",
            mcp_enabled=True,
        )

        # Verify client was created with correct config
        mock_create_client.assert_called_once_with("http://custom-server:8360", "custom-api-key")


class TestMCPIntegrationWithCompoundSystem(unittest.TestCase):
    """Test integration between MCP and compound engineering system."""

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_retrospection_engine_integration(self, mock_create_client):
        """Test RetrospectionEngine can use MCP for logging decisions."""
        mock_client = MagicMock()
        mock_client.vault_log_decision.return_value = "decisions/2025-01-15-test.md"
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Simulate retrospection logging a decision
        result = cei.execute_tool(
            "log_decision",
            project="cohezion",
            title="Use MCP for persistent context",
            context="Need to persist compound engineering insights",
            decision="Integrate Cloud Vault MCP Server",
            rationale="Provides structured knowledge storage with Obsidian",
        )

        self.assertIn("decisions/", result)
        mock_client.vault_log_decision.assert_called_once()

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_skill_refiner_integration(self, mock_create_client):
        """Test SkillRefiner can use MCP for extracting patterns."""
        mock_client = MagicMock()
        mock_client.vault_extract_pattern.return_value = "patterns/compound-feedback-loop.md"
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Simulate skill refiner extracting a pattern
        result = cei.execute_tool(
            "extract_pattern",
            source_path="cohezion/compound/feedback_loop.py",
            pattern_name="Compound Feedback Loop",
            description="Execute → Retrospect → Refine closed loop",
            code_example="executor.execute() → engine.retrospect() → refiner.refine()",
            domain="ml",
        )

        self.assertIn("patterns/", result)
        mock_client.vault_extract_pattern.assert_called_once()

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_journey_persistence_integration(self, mock_create_client):
        """Test JourneyPersistence can use MCP for logging experiments."""
        mock_client = MagicMock()
        mock_client.vault_log_experiment.return_value = "experiments/2025-01-15-journey-tracking.md"
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Simulate journey persistence logging an experiment
        result = cei.execute_tool(
            "log_experiment",
            project="cohezion",
            hypothesis="12D FLUME trajectories capture compound execution quality",
            method="Track phi score across compound operation sequences",
            result="Phi scores range 0.65-0.85 for successful executions",
            learnings="Operation-specific modulation profiles are critical",
        )

        self.assertIn("experiments/", result)
        mock_client.vault_log_experiment.assert_called_once()

    @patch("cohezion.core.context_engineering.create_mcp_client")
    def test_experience_guided_execution(self, mock_create_client):
        """Test compound executor can query prior context for guidance."""
        mock_client = MagicMock()
        mock_client.vault_find_relevant_context.return_value = [
            {
                "path": "decisions/2024-12-01-use-ollama-gate.md",
                "category": "decision",
                "match_count": 5,
            },
            {
                "path": "patterns/concurrency-gate-pattern.md",
                "category": "pattern",
                "match_count": 3,
            },
            {
                "path": "experiments/2024-11-15-semaphore-tuning.md",
                "category": "experiment",
                "match_count": 2,
            },
        ]
        mock_create_client.return_value = mock_client

        cei = ContextEngineeringInfrastructure(
            mcp_server_url="http://localhost:8360",
            mcp_api_key="test-key",
            mcp_enabled=True,
        )

        # Simulate compound executor querying for relevant context
        result = cei.execute_tool(
            "find_relevant_context",
            query="concurrency control for local LLM",
            project="cohezion",
        )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

        # Verify we get decisions, patterns, and experiments
        categories = {r["category"] for r in result}
        self.assertEqual(categories, {"decision", "pattern", "experiment"})


if __name__ == "__main__":
    unittest.main()
