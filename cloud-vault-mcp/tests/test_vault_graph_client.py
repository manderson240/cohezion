# tests/test_vault_graph_client.py
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mcp_server.vault_graph.client import GraphClient, GraphQueryError


def test_graph_client_reads_env_vars(monkeypatch):
    monkeypatch.setenv("SURREALDB_URL", "http://test:9999")
    monkeypatch.setenv("SURREALDB_USERNAME", "testuser")
    monkeypatch.setenv("SURREALDB_PASSWORD", "testpass")
    client = GraphClient()
    assert client.url == "http://test:9999"
    assert client.username == "testuser"


@pytest.mark.asyncio
async def test_query_returns_result_list():
    client = GraphClient()
    mock_db = AsyncMock()
    mock_db.query.return_value = [{"result": [{"title": "Test"}]}]
    with patch.object(client, "_make_connection", return_value=mock_db):
        result = await client.query("SELECT * FROM neuron LIMIT 1")
    assert result == [{"title": "Test"}]


@pytest.mark.asyncio
async def test_query_raises_on_error():
    client = GraphClient()
    mock_db = AsyncMock()
    mock_db.query.return_value = {"code": 400, "description": "syntax error"}
    with patch.object(client, "_make_connection", return_value=mock_db):
        with pytest.raises(GraphQueryError, match="syntax error"):
            await client.query("BAD")
