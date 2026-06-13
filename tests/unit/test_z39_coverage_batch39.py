"""Coverage batch Z39: mcp_tool_defs, scenarios, triune_orchestrator, vault_init, skill_agents, routing_orchestrator, query_patterns."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Pre-inject missing modules so their packages can be imported
# ---------------------------------------------------------------------------

# cohezion.agents.generated.__init__ imports this non-existent submodule
if "cohezion.agents.generated.test_skill_agent" not in sys.modules:
    sys.modules["cohezion.agents.generated.test_skill_agent"] = MagicMock()  # type: ignore[assignment]


# cohezion.real_envs.tasks.scenarios imports cohezion.real_envs.evaluator
@dataclass
class _FileExistsCriterion:
    path: str


@dataclass
class _FileContentCriterion:
    path: str
    expected_pattern: str = ""


@dataclass
class _CommandSucceededCriterion:
    command_pattern: str = ""


@dataclass
class _EvaluatedTask:
    task_id: str
    task_name: str
    description: str
    environment_type: str
    expected_steps: int
    max_steps: int
    criteria: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


_mock_evaluator = MagicMock()
_mock_evaluator.FileExistsCriterion = _FileExistsCriterion
_mock_evaluator.FileContentCriterion = _FileContentCriterion
_mock_evaluator.CommandSucceededCriterion = _CommandSucceededCriterion
_mock_evaluator.EvaluatedTask = _EvaluatedTask

if "cohezion.real_envs.evaluator" not in sys.modules:
    sys.modules["cohezion.real_envs.evaluator"] = _mock_evaluator  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Module 1: skills/mcp_tool_definitions.py
# ---------------------------------------------------------------------------


class TestMcpToolDefinitions:
    def test_base_tools_is_list(self):
        from cohezion.skills.mcp_tool_definitions import BASE_TOOLS

        assert isinstance(BASE_TOOLS, list)
        assert len(BASE_TOOLS) > 0

    def test_base_tools_have_name_and_schema(self):
        from cohezion.skills.mcp_tool_definitions import BASE_TOOLS

        for tool in BASE_TOOLS:
            assert "name" in tool
            assert "inputSchema" in tool

    def test_build_tool_list_empty_skills(self):
        from cohezion.skills.mcp_tool_definitions import BASE_TOOLS, build_tool_list

        result = build_tool_list({})
        assert result == BASE_TOOLS

    def test_build_tool_list_adds_skill_tools(self):
        from cohezion.skills.mcp_tool_definitions import BASE_TOOLS, build_tool_list

        skills = {"CODE_REVIEW": {"description": "Reviews code"}}
        result = build_tool_list(skills)
        assert len(result) == len(BASE_TOOLS) + 1
        names = [t["name"] for t in result]
        assert "skill_code_review" in names

    def test_build_tool_list_skill_has_correct_schema(self):
        from cohezion.skills.mcp_tool_definitions import build_tool_list

        skills = {"MY_SKILL": {"description": "Does stuff"}}
        result = build_tool_list(skills)
        skill_tool = next(t for t in result if t["name"] == "skill_my_skill")
        assert "inputs" in skill_tool["inputSchema"]["properties"]


# ---------------------------------------------------------------------------
# Module 2: real_envs/tasks/scenarios.py
# ---------------------------------------------------------------------------


class TestScenarios:
    def test_create_flask_api_task(self):
        from cohezion.real_envs.tasks.scenarios import create_flask_api_task

        task = create_flask_api_task()
        assert task.task_id == "flask_api_with_db"
        assert len(task.criteria) > 0

    def test_data_pipeline_task(self):
        from cohezion.real_envs.tasks.scenarios import data_pipeline_task

        task = data_pipeline_task()
        assert task.task_id == "data_processing_pipeline"
        assert task.expected_steps == 15

    def test_etl_api_to_db_task(self):
        from cohezion.real_envs.tasks.scenarios import etl_api_to_db_task

        task = etl_api_to_db_task()
        assert task.task_id == "etl_api_to_sqlite"

    def test_git_workflow_automation_task(self):
        from cohezion.real_envs.tasks.scenarios import git_workflow_automation_task

        task = git_workflow_automation_task()
        assert task.task_id == "git_workflow_automation"

    def test_task_registry_contains_all_tasks(self):
        from cohezion.real_envs.tasks.scenarios import TASK_REGISTRY

        assert "flask_api_with_db" in TASK_REGISTRY
        assert "data_processing_pipeline" in TASK_REGISTRY
        assert "etl_api_to_sqlite" in TASK_REGISTRY
        assert "git_workflow_automation" in TASK_REGISTRY


# ---------------------------------------------------------------------------
# Module 3: inference/triune_orchestrator.py
# ---------------------------------------------------------------------------


class TestTriuneOrchestrator:
    def test_build_triune_orchestrator_returns_tiered_orchestrator(self):
        mock_tier = MagicMock()
        mock_orchestrator = MagicMock()

        with (
            patch(
                "cohezion.inference.triune_orchestrator.build_gaia_native_tier",
                return_value=mock_tier,
            ),
            patch(
                "cohezion.inference.triune_orchestrator.TieredOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            from cohezion.inference.triune_orchestrator import build_triune_orchestrator

            result = build_triune_orchestrator()
        assert result is mock_orchestrator

    def test_build_triune_orchestrator_creates_three_tiers(self):
        mock_tier = MagicMock()
        mock_orch_cls = MagicMock()

        with (
            patch(
                "cohezion.inference.triune_orchestrator.build_gaia_native_tier",
                return_value=mock_tier,
            ),
            patch("cohezion.inference.triune_orchestrator.TieredOrchestrator", mock_orch_cls),
        ):
            from cohezion.inference.triune_orchestrator import build_triune_orchestrator

            build_triune_orchestrator()
        _, kwargs = mock_orch_cls.call_args
        tiers = kwargs.get("tiers") or mock_orch_cls.call_args[0][0]
        assert len(tiers) == 3

    def test_build_triune_orchestrator_custom_ports(self):
        mock_tier = MagicMock()
        mock_orch_cls = MagicMock()
        mock_gate = MagicMock()

        with (
            patch(
                "cohezion.inference.triune_orchestrator.build_gaia_native_tier",
                return_value=mock_tier,
            ) as mock_build,
            patch("cohezion.inference.triune_orchestrator.TieredOrchestrator", mock_orch_cls),
            patch("cohezion.inference.triune_orchestrator.QualityGate", mock_gate),
        ):
            from cohezion.inference.triune_orchestrator import build_triune_orchestrator

            build_triune_orchestrator(npu_port=9000, igpu_port=9001, cpu_port=9002)
        # Should have called build_gaia_native_tier 3 times with custom ports
        assert mock_build.call_count == 3


# ---------------------------------------------------------------------------
# Module 4: mcp/servers/vault/__init__.py
# ---------------------------------------------------------------------------


class TestVaultServerInit:
    def test_run_server_calls_vault_main(self):
        mock_vault_main = MagicMock()
        mock_mcp_server = MagicMock(main=mock_vault_main)
        with patch.dict(
            sys.modules, {"mcp_server": mock_mcp_server, "mcp_server.main": mock_mcp_server}
        ):
            import importlib

            import cohezion.mcp.servers.vault as vault_mod

            importlib.reload(vault_mod)
            mock_mcp_server.main = mock_vault_main
            vault_mod.run_server()
        mock_vault_main.assert_called_once()

    def test_main_aliases_run_server(self):
        mock_vault_main = MagicMock()
        mock_mcp_server = MagicMock(main=mock_vault_main)
        with patch.dict(
            sys.modules, {"mcp_server": mock_mcp_server, "mcp_server.main": mock_mcp_server}
        ):
            import cohezion.mcp.servers.vault as vault_mod

            with patch.object(vault_mod, "run_server") as mock_run:
                vault_mod.main()
            mock_run.assert_called_once()

    def test_run_stdio_server_calls_create_server(self):
        mock_config = MagicMock()
        mock_config.from_env.return_value = MagicMock()
        mock_server = MagicMock()
        mock_create = MagicMock(return_value=mock_server)
        mock_mcp_server_config = MagicMock()
        mock_mcp_server_config.ServerConfig = mock_config
        mock_mcp_server_srv = MagicMock()
        mock_mcp_server_srv.create_server = mock_create

        with patch.dict(
            sys.modules,
            {
                "mcp_server": MagicMock(),
                "mcp_server.config": mock_mcp_server_config,
                "mcp_server.server": mock_mcp_server_srv,
            },
        ):
            import importlib

            import cohezion.mcp.servers.vault as vault_mod

            importlib.reload(vault_mod)
            vault_mod.run_stdio_server()
        mock_server.run.assert_called_once()


# ---------------------------------------------------------------------------
# Module 5: agents/generated/skill_0_agent.py + skill_1_agent.py
# ---------------------------------------------------------------------------


class TestGeneratedSkillAgents:
    def test_skill_0_agent_init(self):
        from cohezion.agents.generated.skill_0_agent import Skill0Agent

        agent = Skill0Agent()
        assert agent.SYSTEM_PROMPT == "Domain for skill 0."

    def test_skill_0_agent_with_token_client(self):
        from cohezion.agents.generated.skill_0_agent import Skill0Agent

        mock_client = MagicMock()
        agent = Skill0Agent(token_client=mock_client)
        assert agent._token_client is mock_client

    def test_skill_0_agent_process_calls_executor(self):
        from cohezion.agents.generated.skill_0_agent import Skill0Agent

        mock_result = MagicMock()
        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=mock_result)
        mock_executor_cls = MagicMock(return_value=mock_executor)

        with patch("cohezion.agents.generated.skill_0_agent.PlanExecutor", mock_executor_cls):
            agent = Skill0Agent()
            result = asyncio.run(agent.process("do something"))
        assert result is mock_result

    def test_skill_1_agent_init(self):
        from cohezion.agents.generated.skill_1_agent import Skill1Agent

        agent = Skill1Agent()
        assert agent.SYSTEM_PROMPT == "Domain for skill 1."

    def test_skill_1_agent_process_calls_executor(self):
        from cohezion.agents.generated.skill_1_agent import Skill1Agent

        mock_result = MagicMock()
        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=mock_result)
        mock_executor_cls = MagicMock(return_value=mock_executor)

        with patch("cohezion.agents.generated.skill_1_agent.PlanExecutor", mock_executor_cls):
            agent = Skill1Agent()
            result = asyncio.run(agent.process("do something"))
        assert result is mock_result

    def test_generated_modules_importable_directly(self):
        # The __init__.py has a broken import for test_skill_agent; import submodules directly
        from cohezion.agents.generated.skill_0_agent import Skill0Agent
        from cohezion.agents.generated.skill_1_agent import Skill1Agent

        assert Skill0Agent is not None
        assert Skill1Agent is not None


# ---------------------------------------------------------------------------
# Module 6: swarm/routing_orchestrator.py
# ---------------------------------------------------------------------------


class TestRoutingOrchestrator:
    def test_unified_routing_decision_dataclass(self):
        from cohezion.swarm.routing_orchestrator import UnifiedRoutingDecision

        d = UnifiedRoutingDecision(
            model="phi3:mini",
            confidence=0.7,
            complexity="SIMPLE",
            estimated_tokens=100,
            estimated_cost_usd=0.001,
            reason="test",
        )
        assert d.model == "phi3:mini"
        assert d.constitutional_ok is True
        assert d.can_proceed is True

    def test_route_fallback_when_no_cost_router(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        # Patch _get_cost_router to return None (fallback path)
        with patch.object(orch, "_get_cost_router", return_value=None):
            decision = orch.route("explain this concept")
        assert decision.model == "phi3:mini"
        assert decision.reason == "Fallback routing (no router available)"

    def test_route_with_cost_router_success(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        mock_decision = MagicMock()
        mock_decision.model = "qwen3:7b"
        mock_decision.confidence = 0.9
        mock_decision.complexity.value = "MEDIUM"
        mock_decision.estimated_tokens = 1000
        mock_decision.estimated_cost_usd = 0.003
        mock_decision.reason = "medium task"

        mock_router = MagicMock()
        mock_router.select_model.return_value = (mock_decision, True)

        orch = RoutingOrchestrator()
        with patch.object(orch, "_get_cost_router", return_value=mock_router):
            decision = orch.route("complex task")
        assert decision.model == "qwen3:7b"
        assert decision.can_proceed is True

    def test_route_falls_back_when_cost_router_raises(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        mock_router = MagicMock()
        mock_router.select_model.side_effect = RuntimeError("router error")

        orch = RoutingOrchestrator()
        with patch.object(orch, "_get_cost_router", return_value=mock_router):
            decision = orch.route("something")
        assert decision.model == "phi3:mini"

    def test_get_cost_router_lazy_loads(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        assert orch._cost_router is None
        assert orch._cost_router_loaded is False
        # Let it try to load (it may fail, which is fine)
        orch._get_cost_router()
        assert orch._cost_router_loaded is True

    def test_get_confidence_fallback(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        with patch.object(orch, "_get_cost_router", return_value=None):
            confidence = orch.get_confidence("phi3:mini", "simple task")
        assert confidence == pytest.approx(0.5)

    def test_get_confidence_with_router_success(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        mock_router = MagicMock()
        mock_router.complexity_analyzer.analyze.return_value = "SIMPLE"
        mock_router._compute_routing_confidence.return_value = 0.8

        orch = RoutingOrchestrator()
        with patch.object(orch, "_get_cost_router", return_value=mock_router):
            confidence = orch.get_confidence("phi3:mini", "simple task")
        assert confidence == pytest.approx(0.8)

    def test_get_confidence_falls_back_when_router_raises(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        mock_router = MagicMock()
        mock_router.complexity_analyzer.analyze.side_effect = RuntimeError("oops")

        orch = RoutingOrchestrator()
        with patch.object(orch, "_get_cost_router", return_value=mock_router):
            confidence = orch.get_confidence("phi3:mini", "something")
        assert confidence == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Module 7: core/persistence/query_patterns.py
# ---------------------------------------------------------------------------


class TestQueryPatterns:
    def test_query_patterns_function_runs_with_mock_surreal(self):
        mock_db = AsyncMock()
        mock_db.signin = AsyncMock()
        mock_db.use = AsyncMock()
        mock_db.query = AsyncMock(return_value=[{"result": []}])

        mock_surreal_ctx = AsyncMock()
        mock_surreal_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_surreal_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_surreal_cls = MagicMock(return_value=mock_surreal_ctx)

        with patch("cohezion.core.persistence.query_patterns.AsyncSurreal", mock_surreal_cls):
            from cohezion.core.persistence.query_patterns import query_patterns

            asyncio.run(query_patterns())
        mock_db.signin.assert_awaited_once()
        mock_db.use.assert_awaited_once_with("cohezion", "universe")
        assert mock_db.query.await_count == 2
