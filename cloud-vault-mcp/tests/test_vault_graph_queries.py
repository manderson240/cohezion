# tests/test_vault_graph_queries.py
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mcp_server.vault_graph import queries


@pytest.mark.asyncio
async def test_search_calls_correct_function():
    mock_client = AsyncMock()
    mock_client.query.return_value = [{"title": "Quantum"}]
    with patch("mcp_server.vault_graph.queries.get_graph_client", return_value=mock_client):
        result = await queries.search("quantum")
    call_sql = mock_client.query.call_args[0][0]
    assert "fn::context_search" in call_sql
    assert "quantum" in call_sql


@pytest.mark.asyncio
async def test_stats_calls_vault_stats():
    mock_client = AsyncMock()
    mock_client.query.return_value = [{"total_neurons": 1578}]
    with patch("mcp_server.vault_graph.queries.get_graph_client", return_value=mock_client):
        result = await queries.stats()
    call_sql = mock_client.query.call_args[0][0]
    assert "fn::vault_stats" in call_sql
