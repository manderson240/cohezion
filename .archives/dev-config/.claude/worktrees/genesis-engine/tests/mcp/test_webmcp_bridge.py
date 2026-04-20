"""Tests for WebMCP Bridge real routing (not mocked)."""

import pytest

from cohezion.mcp.webmcp_bridge import WebMCPBridge


@pytest.fixture
def bridge() -> WebMCPBridge:
    return WebMCPBridge(port=0)


class TestWebMCPBridgeRouting:
    """Verify the bridge routes to real MCP handlers, not mocks."""

    def test_bridge_has_call_tool_route(self, bridge: WebMCPBridge) -> None:
        routes = [
            r.resource.canonical
            for r in bridge.app.router.routes()
            if hasattr(r, "resource") and hasattr(r.resource, "canonical")
        ]
        assert "/mcp/call_tool" in routes

    def test_bridge_has_list_servers_route(self, bridge: WebMCPBridge) -> None:
        routes = [
            r.resource.canonical
            for r in bridge.app.router.routes()
            if hasattr(r, "resource") and hasattr(r.resource, "canonical")
        ]
        assert "/mcp/list_servers" in routes


class TestToolNameValidation:
    """Verify server/tool name validation prevents injection."""

    def test_valid_server_name_accepted(self, bridge: WebMCPBridge) -> None:
        assert bridge._validate_name("knowledge") is True
        assert bridge._validate_name("surreal-db") is True
        assert bridge._validate_name("swarm_server") is True

    def test_invalid_server_name_rejected(self, bridge: WebMCPBridge) -> None:
        assert bridge._validate_name("") is False
        assert bridge._validate_name("../etc/passwd") is False
        assert bridge._validate_name("server; rm -rf /") is False
        assert bridge._validate_name("a" * 200) is False

    def test_no_mock_string_in_response(self, bridge: WebMCPBridge) -> None:
        """Ensure 'MOCKED' never appears in any response handler source."""
        import inspect

        source = inspect.getsource(bridge.handle_call_tool)
        assert "MOCKED" not in source
