# tests/test_vault_graph_tools.py
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest


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
        # fn::vault_stats() returns counts as [{count: N}] subquery arrays
        mock_q.stats = AsyncMock(
            return_value={
                "total_neurons": [{"count": 1578}],
                "total_synapses": [{"count": 6203}],
                "stage_distribution": [],
            }
        )
        result = await tools.tool_graph_stats()
    assert "1578" in result
    assert "6203" in result


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
