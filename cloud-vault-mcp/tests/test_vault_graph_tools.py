# tests/test_vault_graph_tools.py
import pytest
from unittest.mock import AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mcp_server.vault_graph import tools


@pytest.mark.asyncio
async def test_tool_graph_search_calls_queries_search():
    with patch("mcp_server.vault_graph.tools.queries") as mock_q:
        mock_q.search = AsyncMock(return_value=[{"title": "Quantum"}])
        result = await tools.tool_graph_search(query="quantum")
    mock_q.search.assert_called_once_with("quantum")
    assert "Quantum" in result


@pytest.mark.asyncio
async def test_tool_graph_stats_returns_stats():
    with patch("mcp_server.vault_graph.tools.queries") as mock_q:
        mock_q.stats = AsyncMock(return_value={"total_neurons": 1578, "total_synapses": 6203})
        result = await tools.tool_graph_stats()
    assert "1578" in result


@pytest.mark.asyncio
async def test_tool_graph_neighborhood_formats_output():
    mock_data = {
        "neuron": {"title": "Test", "activation": 0.9, "stage": "mature", "cluster_id": "cortex"},
        "outbound": [],
        "inbound": [],
        "cluster_top": [],
    }
    with patch("mcp_server.vault_graph.tools.queries") as mock_q:
        mock_q.neighborhood = AsyncMock(return_value=mock_data)
        result = await tools.tool_graph_neighborhood(neuron_id="neuron:test_md")
    assert "Test" in result
