"""Coverage batch Z58: api_routes_swarm, api_routes_skills."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: api/routes/swarm.py
# ---------------------------------------------------------------------------


class TestSwarmRoutes:
    def _make_mock_server(self):
        mock_server = MagicMock()
        mock_server.run_debate.return_value = {
            "content": "balanced view",
            "confidence": 0.8,
            "model_chain": ["phi3:mini"],
            "processing_time_ms": 100.0,
        }
        mock_server.get_perspectives.return_value = ["optimist", "realist", "critic"]
        mock_server.get_metrics.return_value = {"total_debates": 5, "avg_confidence": 0.75}
        return mock_server

    def test_get_perspectives(self):
        from cohezion.api.routes.swarm import get_perspectives

        mock_server = self._make_mock_server()
        with patch("cohezion.api.routes.swarm.get_swarm_server", return_value=mock_server):
            result = asyncio.run(get_perspectives())
        assert "perspectives" in result
        assert len(result["perspectives"]) == 3

    def test_get_metrics(self):
        from cohezion.api.routes.swarm import get_metrics

        mock_server = self._make_mock_server()
        with patch("cohezion.api.routes.swarm.get_swarm_server", return_value=mock_server):
            result = asyncio.run(get_metrics())
        assert "metrics" in result
        assert result["metrics"]["total_debates"] == 5

    def test_run_debate_success(self):
        from cohezion.api.routes.swarm import DebateRequest, run_debate

        mock_server = self._make_mock_server()
        with patch("cohezion.api.routes.swarm.get_swarm_server", return_value=mock_server):
            request = DebateRequest(query="Is AGI here?", perspectives=["optimist"])
            result = asyncio.run(run_debate(request))
        assert result.content == "balanced view"
        assert result.confidence == pytest.approx(0.8)

    def test_run_debate_server_error_raises_http(self):
        from fastapi import HTTPException

        from cohezion.api.routes.swarm import DebateRequest, run_debate

        mock_server = MagicMock()
        mock_server.run_debate.side_effect = Exception("server crash")
        with patch("cohezion.api.routes.swarm.get_swarm_server", return_value=mock_server):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(run_debate(DebateRequest(query="test")))
        assert exc_info.value.status_code == 500

    def test_swarm_models(self):
        from cohezion.api.routes.swarm import DebateResponse, SwarmExecuteRequest, SwarmExecuteResponse

        resp = DebateResponse(content="c", confidence=0.9, model_chain=["m"], processing_time_ms=10.0)
        assert resp.confidence == pytest.approx(0.9)

        req = SwarmExecuteRequest(intent="do something")
        assert req.max_agents == 4

        swarm_resp = SwarmExecuteResponse(report_id="r1", status="completed")
        assert swarm_resp.tasks == []


# ---------------------------------------------------------------------------
# Module 2: api/routes/skills.py
# ---------------------------------------------------------------------------


class TestSkillsRoutes:
    def test_skill_execute_request_model(self):
        from cohezion.api.routes.skills import SkillExecuteRequest

        req = SkillExecuteRequest(input_text="review this code", config={"verbose": True})
        assert req.input_text == "review this code"
        assert req.config == {"verbose": True}

    def test_capability_query_request_model(self):
        from cohezion.api.routes.skills import CapabilityQueryRequest

        req = CapabilityQueryRequest(query="find debugging agent", top_k=3)
        assert req.top_k == 3

    def test_find_capable_agent(self):
        from cohezion.api.routes.skills import CapabilityQueryRequest, find_capable_agent

        mock_cap = MagicMock()
        mock_cap.name = "debugger"
        mock_cap.type = "agent"
        mock_cap.description = "debugs code"
        mock_cap.score = 0.9
        mock_cap.path = "path/to/agent"

        mock_registry = MagicMock()
        mock_registry.find.return_value = [mock_cap]
        mock_cls = MagicMock(return_value=mock_registry)

        # Lazy import inside function — patch at source
        with patch("cohezion.registry.capability_registry.CapabilityRegistry", mock_cls):
            req = CapabilityQueryRequest(query="debug", top_k=3)
            result = asyncio.run(find_capable_agent(req))
        assert result.query == "debug"
        assert len(result.agents) == 1
        assert result.agents[0]["name"] == "debugger"

    def test_list_prime_skills(self):
        from cohezion.api.routes.skills import list_prime_skills

        mock_factory = MagicMock()
        mock_factory.list_available_skills.return_value = ["CODE_REVIEW", "TEST_GEN", "REFACTOR"]
        mock_cls = MagicMock(return_value=mock_factory)

        # Lazy import inside function — patch at source
        with patch("cohezion.agents.factory.AgentFactory", mock_cls):
            result = asyncio.run(list_prime_skills())
        assert result["count"] == 3
        assert "CODE_REVIEW" in result["skills"]

    def test_execute_skill_not_found_raises_404(self):
        from fastapi import HTTPException

        from cohezion.api.routes.skills import SkillExecuteRequest, execute_skill

        with patch("cohezion.agents.factory.AgentFactory") as mock_cls:
            mock_factory = MagicMock()
            mock_factory._resolve_spec.side_effect = KeyError("UNKNOWN_SKILL")
            mock_cls.return_value = mock_factory
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(execute_skill("UNKNOWN_SKILL", SkillExecuteRequest(input_text="test")))
        assert exc_info.value.status_code == 404
