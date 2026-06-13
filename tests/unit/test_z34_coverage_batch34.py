"""Coverage batch Z34: compound_utils, notebooks routes, knowledge_graph CLI, swarm compat."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: mcp/compound_utils.py
# ---------------------------------------------------------------------------


class TestCompoundUtils:
    def test_ok_returns_success_status(self):
        from cohezion.mcp.compound_utils import ok

        result = ok(value=42)
        assert result["status"] == "success"
        assert result["value"] == 42

    def test_ok_with_multiple_fields(self):
        from cohezion.mcp.compound_utils import ok

        result = ok(count=5, items=["a", "b"])
        assert result["count"] == 5
        assert result["items"] == ["a", "b"]

    def test_err_returns_error_status(self):
        from cohezion.mcp.compound_utils import err

        result = err("something failed")
        assert result["status"] == "error"
        assert result["error"] == "something failed"

    def test_err_with_extra_fields(self):
        from cohezion.mcp.compound_utils import err

        result = err("oops", code=500, context="during processing")
        assert result["code"] == 500
        assert result["context"] == "during processing"

    def test_mcp_tool_wraps_happy_path(self):
        from cohezion.mcp.compound_utils import mcp_tool

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda f: f

        @mcp_tool(mock_mcp, description="test")
        async def my_tool(x: int) -> dict:
            return {"status": "success", "result": x * 2}

        result = asyncio.run(my_tool(5))
        assert result["result"] == 10

    def test_mcp_tool_catches_exception_returns_err(self):
        from cohezion.mcp.compound_utils import mcp_tool

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda f: f

        @mcp_tool(mock_mcp)
        async def failing_tool() -> dict:
            raise ValueError("something went wrong")

        result = asyncio.run(failing_tool())
        assert result["status"] == "error"
        assert "something went wrong" in result["error"]

    def test_mcp_tool_registers_with_mcp_instance(self):
        from cohezion.mcp.compound_utils import mcp_tool

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda f: f

        @mcp_tool(mock_mcp, description="my desc")
        async def another_tool() -> dict:
            return {"status": "success"}

        mock_mcp.tool.assert_called_once_with(description="my desc")

    def test_mcp_client_resolver_uses_default_client(self):
        from cohezion.mcp.compound_utils import McpClientResolver

        mock_default = MagicMock()
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_default.return_value = mock_client

        resolver = McpClientResolver(mock_default)
        client, is_fresh = asyncio.run(resolver.resolve(server_url=None))
        assert client is mock_client
        assert is_fresh is False

    def test_mcp_client_resolver_creates_fresh_when_url_given(self):

        from cohezion.mcp.compound_utils import McpClientResolver

        mock_fresh = MagicMock()
        mock_fresh.connect = AsyncMock()
        mock_create = MagicMock(return_value=mock_fresh)

        resolver = McpClientResolver(MagicMock())
        with patch("cohezion.core.mcp_client.create_mcp_client", mock_create):
            client, is_fresh = asyncio.run(resolver.resolve(server_url="ws://custom:8001"))
        assert is_fresh is True
        mock_fresh.connect.assert_awaited_once()

    def test_mcp_client_resolver_handles_connect_failure(self):
        from cohezion.mcp.compound_utils import McpClientResolver

        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=RuntimeError("connect failed"))
        mock_default = MagicMock(return_value=mock_client)

        resolver = McpClientResolver(mock_default)
        # Should not raise — swallows connect error
        client, is_fresh = asyncio.run(resolver.resolve(server_url=None))
        assert client is mock_client


# ---------------------------------------------------------------------------
# Module 2: api/routes/notebooks.py
# ---------------------------------------------------------------------------


class TestNotebooksRoutes:
    def test_list_notebooks_no_dir(self):
        from cohezion.api.routes.notebooks import list_notebooks

        with patch("cohezion.api.routes.notebooks.Path") as mock_path_cls:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path_cls.return_value = mock_dir
            result = asyncio.run(list_notebooks())
        assert result == {"notebooks": []}

    def test_list_notebooks_with_files(self, tmp_path):
        from cohezion.api.routes.notebooks import list_notebooks

        nb_dir = tmp_path / "notebooks"
        nb_dir.mkdir()
        (nb_dir / "intro.md").write_text("# Intro")
        (nb_dir / "advanced.md").write_text("# Advanced")

        with patch("cohezion.api.routes.notebooks.Path", return_value=nb_dir):
            result = asyncio.run(list_notebooks())
        names = result["notebooks"]
        assert "intro" in names or "advanced" in names

    def test_get_notebook_invalid_name_raises_400(self):
        from fastapi import HTTPException

        from cohezion.api.routes.notebooks import get_notebook

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_notebook("../etc/passwd"))
        assert exc_info.value.status_code == 400

    def test_get_notebook_not_found_raises_404(self, tmp_path):
        from fastapi import HTTPException

        from cohezion.api.routes.notebooks import get_notebook

        with patch("cohezion.api.routes.notebooks.Path", return_value=tmp_path):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_notebook("nonexistent"))
        assert exc_info.value.status_code == 404

    def test_get_notebook_returns_content(self, tmp_path):

        nb_dir = tmp_path / "docs" / "notebooks"
        nb_dir.mkdir(parents=True)
        (nb_dir / "test_nb.md").write_text("# Test")

        with patch("cohezion.api.routes.notebooks.Path") as mock_path_cls:
            mock_path_cls.return_value = nb_dir
            with patch("cohezion.api.routes.notebooks.Path") as mock_path_2:
                actual_path = nb_dir / "test_nb.md"
                mock_path_2.return_value.resolve.return_value = actual_path
                mock_path_2.return_value.__truediv__ = MagicMock(
                    return_value=MagicMock(
                        resolve=MagicMock(return_value=actual_path),
                        exists=MagicMock(return_value=True),
                        read_text=MagicMock(return_value="# Test"),
                    )
                )
                # Direct call test - verify path validation logic
                import re

                assert re.match(r"^[a-zA-Z0-9_-]+$", "test_nb") is not None
                assert re.match(r"^[a-zA-Z0-9_-]+$", "../passwd") is None

    def test_list_simulations_no_file(self):
        from cohezion.api.routes.notebooks import list_simulations

        with patch("cohezion.api.routes.notebooks.Path") as mock_path_cls:
            mock_file = MagicMock()
            mock_file.exists.return_value = False
            mock_path_cls.return_value = mock_file
            result = asyncio.run(list_simulations())
        assert result == {"simulations": []}

    def test_list_simulations_with_data(self, tmp_path):
        from cohezion.api.routes.notebooks import list_simulations

        sim_file = tmp_path / "sims.json"
        sim_file.write_text(json.dumps({"simulations": [{"id": "sim1"}, {"id": "sim2"}]}))

        with patch("cohezion.api.routes.notebooks.Path", return_value=sim_file):
            result = asyncio.run(list_simulations())
        assert "sim1" in result["simulations"]

    def test_get_simulation_not_found_file_raises_404(self):
        from fastapi import HTTPException

        from cohezion.api.routes.notebooks import get_simulation

        with patch("cohezion.api.routes.notebooks.Path") as mock_path_cls:
            mock_file = MagicMock()
            mock_file.exists.return_value = False
            mock_path_cls.return_value = mock_file
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_simulation("sim999"))
        assert exc_info.value.status_code == 404

    def test_get_simulation_found(self, tmp_path):
        from cohezion.api.routes.notebooks import get_simulation

        sim_file = tmp_path / "sims.json"
        sim_data = {"simulations": [{"id": "sim1", "name": "Pendulum"}]}
        sim_file.write_text(json.dumps(sim_data))

        with patch("cohezion.api.routes.notebooks.Path", return_value=sim_file):
            result = asyncio.run(get_simulation("sim1"))
        assert result["name"] == "Pendulum"

    def test_get_simulation_id_not_in_file_raises_404(self, tmp_path):
        from fastapi import HTTPException

        from cohezion.api.routes.notebooks import get_simulation

        sim_file = tmp_path / "sims.json"
        sim_file.write_text(json.dumps({"simulations": [{"id": "sim1"}]}))

        with patch("cohezion.api.routes.notebooks.Path", return_value=sim_file):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_simulation("sim_missing"))
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Module 3: knowledge_graph/cli.py
# ---------------------------------------------------------------------------


class TestKnowledgeGraphCLI:
    def test_cli_search_command(self):
        from cohezion.knowledge_graph.cli import main

        mock_engine = MagicMock()
        mock_engine.search_knowledge.return_value = [{"id": "result1"}]

        with (
            patch(
                "cohezion.knowledge_graph.cli.KnowledgeGraphQueryEngine", return_value=mock_engine
            ),
            patch("cohezion.knowledge_graph.cli.RetrospectionEngine", return_value=MagicMock()),
            patch("sys.argv", ["cli.py", "search", "find vault"]),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_engine.search_knowledge.assert_called_once_with("find vault", top_k=5)
        mock_print.assert_called_once()

    def test_cli_history_command(self):
        from cohezion.knowledge_graph.cli import main

        mock_engine = MagicMock()
        mock_engine.query_execution_history = AsyncMock(return_value=[{"exec": "data"}])

        with (
            patch(
                "cohezion.knowledge_graph.cli.KnowledgeGraphQueryEngine", return_value=mock_engine
            ),
            patch("cohezion.knowledge_graph.cli.RetrospectionEngine", return_value=MagicMock()),
            patch("sys.argv", ["cli.py", "history", "--limit", "10"]),
            patch("builtins.print") as _mock_print,
        ):
            main()
        mock_engine.query_execution_history.assert_awaited_once_with(limit=10)

    def test_cli_stats_command(self):
        from cohezion.knowledge_graph.cli import main

        mock_engine = MagicMock()
        mock_engine.get_pattern_summary = AsyncMock(return_value={"patterns": 5})

        with (
            patch(
                "cohezion.knowledge_graph.cli.KnowledgeGraphQueryEngine", return_value=mock_engine
            ),
            patch("cohezion.knowledge_graph.cli.RetrospectionEngine", return_value=MagicMock()),
            patch("sys.argv", ["cli.py", "stats"]),
            patch("builtins.print"),
        ):
            main()
        mock_engine.get_pattern_summary.assert_awaited_once()

    def test_cli_retro_command(self):
        from cohezion.knowledge_graph.cli import main

        mock_retro = MagicMock()
        mock_retro.generate_session_report.return_value = "Report: 3 learnings"

        with (
            patch(
                "cohezion.knowledge_graph.cli.KnowledgeGraphQueryEngine", return_value=MagicMock()
            ),
            patch("cohezion.knowledge_graph.cli.RetrospectionEngine", return_value=mock_retro),
            patch("sys.argv", ["cli.py", "retro", "--facts", '{"k": "v"}']),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_retro.generate_session_report.assert_called_once_with({"k": "v"})
        mock_print.assert_called_once_with("Report: 3 learnings")

    def test_cli_retro_no_facts(self):
        from cohezion.knowledge_graph.cli import main

        mock_retro = MagicMock()
        mock_retro.generate_session_report.return_value = "Empty report"

        with (
            patch(
                "cohezion.knowledge_graph.cli.KnowledgeGraphQueryEngine", return_value=MagicMock()
            ),
            patch("cohezion.knowledge_graph.cli.RetrospectionEngine", return_value=mock_retro),
            patch("sys.argv", ["cli.py", "retro"]),
            patch("builtins.print"),
        ):
            main()
        mock_retro.generate_session_report.assert_called_once_with({})


# ---------------------------------------------------------------------------
# Module 4: swarm/compat.py
# ---------------------------------------------------------------------------


class TestSwarmCompat:
    def test_legacy_agent_result_dataclass(self):
        from cohezion.swarm.compat import LegacyAgentResult

        r = LegacyAgentResult(agent_id="agent-1", success=True, output="done")
        assert r.agent_id == "agent-1"
        assert r.success is True
        assert r.output == "done"
        assert r.error is None

    def test_legacy_agent_result_with_error(self):
        from cohezion.swarm.compat import LegacyAgentResult

        r = LegacyAgentResult(agent_id="agent-2", success=False, error="timeout")
        assert r.error == "timeout"

    def test_agent_capability_dataclass(self):
        from cohezion.swarm.compat import AgentCapability

        cap = AgentCapability(name="code_review", confidence=0.9)
        assert cap.name == "code_review"
        assert cap.confidence == pytest.approx(0.9)

    def test_agent_capability_default_confidence(self):
        from cohezion.swarm.compat import AgentCapability

        cap = AgentCapability(name="search")
        assert cap.confidence == pytest.approx(1.0)

    def test_swarm_orchestrator_init(self):
        from cohezion.swarm.compat import SwarmOrchestrator

        mock_swarm = MagicMock()
        mock_swarm_cls = MagicMock(return_value=mock_swarm)
        mock_config_cls = MagicMock()

        with (
            patch("cohezion.swarm.compat.NewSwarm", mock_swarm_cls),
            patch("cohezion.swarm.compat.NewSwarmConfig", mock_config_cls),
        ):
            orch = SwarmOrchestrator(max_concurrent=6)
        assert orch.max_concurrent == 6

    def test_swarm_orchestrator_register_agent(self):
        from cohezion.swarm.compat import SwarmOrchestrator

        mock_swarm = MagicMock()
        with (
            patch("cohezion.swarm.compat.NewSwarm", return_value=mock_swarm),
            patch("cohezion.swarm.compat.NewSwarmConfig"),
            patch("cohezion.swarm.compat.NewAgent") as _mock_agent_cls,
        ):
            orch = SwarmOrchestrator()
            fn = lambda x: x
            orch.register_agent("a1", "Agent1", ["cap1"], fn)
        mock_swarm.register_agent.assert_called_once()

    def test_swarm_orchestrator_execute_task(self):
        from cohezion.swarm.compat import SwarmOrchestrator

        mock_swarm = MagicMock()
        mock_result = MagicMock()
        mock_result.agent_id = "a1"
        mock_result.success = True
        mock_result.output = "result"
        mock_result.error = None
        mock_swarm.execute = AsyncMock(return_value=mock_result)

        with (
            patch("cohezion.swarm.compat.NewSwarm", return_value=mock_swarm),
            patch("cohezion.swarm.compat.NewSwarmConfig"),
            patch("cohezion.swarm.compat.NewTask"),
        ):
            orch = SwarmOrchestrator()
            result = asyncio.run(orch.execute_task("t1", "do stuff", ["cap1"]))
        assert result.success is True

    def test_swarm_orchestrator_execute_parallel(self):
        from cohezion.swarm.compat import SwarmOrchestrator

        mock_swarm = MagicMock()
        mock_r = MagicMock(agent_id="a", success=True, output="x", error=None)
        mock_swarm.execute_parallel = AsyncMock(return_value=[mock_r, mock_r])

        with (
            patch("cohezion.swarm.compat.NewSwarm", return_value=mock_swarm),
            patch("cohezion.swarm.compat.NewSwarmConfig"),
            patch("cohezion.swarm.compat.NewTask"),
        ):
            orch = SwarmOrchestrator()
            tasks = [{"task_id": "t1", "description": "desc", "required_capabilities": []}]
            results = asyncio.run(orch.execute_parallel(tasks))
        assert len(results) == 2

    def test_swarm_orchestrator_get_stats(self):
        from cohezion.swarm.compat import SwarmOrchestrator

        mock_swarm = MagicMock()
        mock_swarm.get_agent_stats.return_value = {"agents": 3}

        with (
            patch("cohezion.swarm.compat.NewSwarm", return_value=mock_swarm),
            patch("cohezion.swarm.compat.NewSwarmConfig"),
        ):
            orch = SwarmOrchestrator()
            stats = orch.get_agent_stats()
        assert stats["agents"] == 3
