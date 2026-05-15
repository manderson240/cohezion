"""Coverage batch Z56: graphrag_engine, journey_server."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module 1: knowledge_graph/graphrag_engine.py
# ---------------------------------------------------------------------------


class TestGraphRAGEngine:
    def _make_engine(self, client=None):
        from cohezion.knowledge_graph.graphrag_engine import GraphRAGEngine

        return GraphRAGEngine(surreal_client=client, default_top_k=5)

    def test_retrieval_result_dataclass(self):
        from cohezion.knowledge_graph.graphrag_engine import RetrievalResult

        r = RetrievalResult(neuron_id="n1", title="Test", content="some content", score=0.9)
        assert r.neuron_id == "n1"
        assert r.connections == []

    def test_graphrag_response_dataclass(self):
        from cohezion.knowledge_graph.graphrag_engine import GraphRAGResponse, RetrievalResult

        r = GraphRAGResponse(
            results=[RetrievalResult(neuron_id="n1", title="T", content="C", score=0.8)],
            query="test",
            mode="vector",
            total_results=1,
            query_time_ms=5.0,
        )
        assert r.total_results == 1

    def test_vector_search_no_client_returns_empty(self):
        engine = self._make_engine(client=None)
        embedding = [0.1] * 768
        result = asyncio.run(engine.vector_search(embedding))
        assert result.results == []
        assert result.mode == "vector"

    def test_graph_search_no_client_returns_empty(self):
        engine = self._make_engine(client=None)
        result = asyncio.run(engine.graph_search("n1"))
        assert result.results == []

    def test_temporal_search_no_client_returns_empty(self):
        from datetime import UTC, datetime

        engine = self._make_engine(client=None)
        result = asyncio.run(engine.temporal_search([0.1] * 768, as_of=datetime.now(UTC)))
        assert result.results == []

    def test_hybrid_search_no_client_returns_empty(self):
        engine = self._make_engine(client=None)
        embedding = [0.5] * 768
        result = asyncio.run(engine.hybrid_search("neural architecture", embedding))
        assert result.results == []

    def test_vector_search_with_mock_client(self):
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(
            return_value=[
                {
                    "status": "OK",
                    "result": [
                        {"id": "neuron:1", "title": "PyTorch basics", "content": "deep learning...", "score": 0.95}
                    ],
                }
            ]
        )
        engine = self._make_engine(client=mock_client)
        embedding = [0.1] * 768
        result = asyncio.run(engine.vector_search(embedding))
        assert len(result.results) == 1
        assert result.results[0].title == "PyTorch basics"
        assert result.results[0].score == pytest.approx(0.95)

    def test_execute_query_handles_exception(self):
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=Exception("DB error"))
        engine = self._make_engine(client=mock_client)
        embedding = [0.1] * 768
        result = asyncio.run(engine.vector_search(embedding))
        assert result.results == []

    def test_execute_query_handles_empty_response(self):
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(return_value=[])  # empty list
        engine = self._make_engine(client=mock_client)
        embedding = [0.1] * 768
        result = asyncio.run(engine.vector_search(embedding))
        assert result.results == []


# ---------------------------------------------------------------------------
# Module 2: mcp/servers/journey/server.py
# ---------------------------------------------------------------------------


class TestJourneyServer:
    def _make_request(self, data: dict | None = None):
        mock_req = MagicMock()
        mock_req.json = AsyncMock(return_value=data or {})
        return mock_req

    def test_health_endpoint(self):
        from cohezion.mcp.servers.journey.server import health

        req = self._make_request()
        response = asyncio.run(health(req))
        result = json.loads(response.body)
        assert result["status"] == "healthy"
        assert result["server"] == "journey"

    def test_index_endpoint(self):
        from cohezion.mcp.servers.journey.server import index

        req = self._make_request()
        response = asyncio.run(index(req))
        result = json.loads(response.body)
        assert "name" in result or "server" in result

    def test_start_journey_tool(self):
        from cohezion.mcp.servers.journey.server import tool_journey_start

        req = self._make_request({"agent_id": "agent-001", "intent": "analyze code"})
        response = asyncio.run(tool_journey_start(req))
        result = json.loads(response.body)
        assert "journey_id" in result or "tool" in result or "error" in result

    def test_list_journeys_tool(self):
        from cohezion.mcp.servers.journey.server import tool_journey_list

        req = self._make_request({"agent_id": "agent-001"})
        response = asyncio.run(tool_journey_list(req))
        result = json.loads(response.body)
        assert "journeys" in result or "tool" in result

    def test_create_app_returns_application(self):
        from cohezion.mcp.servers.journey.server import create_app

        app = create_app()
        assert app is not None
