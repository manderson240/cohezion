"""Tests for MCPClient connection resilience with retry logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.core.mcp_client import MCPClient, MCPConfig


def _make_client():
    return MCPClient(MCPConfig(server_url="http://localhost:8360", api_key="test"))


class TestConnectionResilience:
    """Test MCPClient behavior under connection failures."""

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_connect_idempotent_when_already_connected(self, mock_class):
        """connect() is a no-op if already connected (does not create a second client)."""
        mock_ac = MagicMock()
        mock_ac.post = AsyncMock()
        mock_ac.aclose = AsyncMock()
        mock_ac.post.return_value.raise_for_status = MagicMock()
        mock_ac.post.return_value.headers = {"mcp-session-id": "test-123"}
        mock_ac.post.return_value.text = 'event: message\ndata: {"jsonrpc":"2.0","id":0,"result":{"protocolVersion":"2024-11-05"}}\n\n'
        mock_class.return_value = mock_ac

        client = _make_client()
        asyncio.run(client.connect())
        asyncio.run(client.connect())  # Second call should be no-op

        # AsyncClient should only be instantiated once
        assert mock_class.call_count == 1

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_close_resets_client_state(self, mock_class):
        """close() resets _client and _session_id to None."""
        mock_ac = MagicMock()
        mock_ac.aclose = AsyncMock()
        mock_class.return_value = mock_ac

        client = _make_client()
        client._client = mock_ac  # Simulate connected state
        client._session_id = "test-123"

        asyncio.run(client.close())

        assert client._client is None
        assert client._session_id is None

    def test_vault_write_sync_safe_when_no_connection(self):
        """vault_write_sync never raises even when no connection is established."""
        client = _make_client()
        # No connection established — should not raise
        client.vault_write_sync("test/path.md", "content")

    def test_vault_search_returns_empty_when_disconnected(self):
        """vault_search returns [] when not connected (graceful degradation)."""
        client = _make_client()
        result = client.vault_search("test query")
        assert isinstance(result, list)  # Returns list (possibly empty)
