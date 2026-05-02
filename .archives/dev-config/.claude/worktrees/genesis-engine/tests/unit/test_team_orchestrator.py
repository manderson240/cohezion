"""Tests for the TeamOrchestrator."""

import pytest

from cohezion.swarm.team_orchestrator import (
    AgentSpec,
    TaskSpec,
    TeamOrchestrator,
    TeamPlan,
)


@pytest.fixture
def orchestrator():
    return TeamOrchestrator()


class TestPlanTeam:
    def test_plan_team_returns_teamplan(self, orchestrator):
        plan = orchestrator.plan_team("add error handling to API")
        assert isinstance(plan, TeamPlan)
        assert plan.intent == "add error handling to API"

    def test_plan_has_agents(self, orchestrator):
        plan = orchestrator.plan_team("physics simulation")
        assert isinstance(plan.agents, list)
        for agent in plan.agents:
            assert isinstance(agent, AgentSpec)
            assert agent.name

    def test_plan_has_tasks(self, orchestrator):
        plan = orchestrator.plan_team("implement circuit breaker")
        assert isinstance(plan.tasks, list)
        assert len(plan.tasks) >= 1
        for task in plan.tasks:
            assert isinstance(task, TaskSpec)

    def test_max_agents_respected(self, orchestrator):
        plan = orchestrator.plan_team("everything", max_agents=2)
        assert len(plan.agents) <= 2

    def test_plan_summary(self, orchestrator):
        plan = orchestrator.plan_team("test plan")
        summary = plan.summary
        assert "Team:" in summary
        assert "Intent:" in summary


class TestGenerateAgentSpec:
    def test_generates_spec_for_known_skill(self, orchestrator):
        spec = orchestrator.generate_agent_spec("COMPOUND_ENGINEERING_PRIME")
        assert isinstance(spec, AgentSpec)
        assert spec.name

    def test_generates_fallback_for_unknown_skill(self, orchestrator):
        spec = orchestrator.generate_agent_spec("NONEXISTENT_SKILL_PRIME")
        assert isinstance(spec, AgentSpec)
        assert spec.name


class TestSelectModel:
    def test_test_tasks_route_to_phi3(self, orchestrator):
        task = TaskSpec(id="t1", subject="Run tests", description="verify", tags=["test"])
        model = orchestrator.select_model(task)
        assert model == "phi3:mini"

    def test_code_tasks_route_to_qwen(self, orchestrator):
        task = TaskSpec(id="t2", subject="Implement feature", description="implement", tags=["code"])
        model = orchestrator.select_model(task)
        assert model == "qwen3-coder:30b"

    def test_reasoning_tasks_route_to_deepseek(self, orchestrator):
        task = TaskSpec(
            id="t3",
            subject="Design architecture",
            description="architect",
            tags=["plan"],
        )
        model = orchestrator.select_model(task)
        assert model == "deepseek-r1:70b"

    def test_default_is_phi3(self, orchestrator):
        task = TaskSpec(id="t4", subject="Unknown", description="something", tags=[])
        model = orchestrator.select_model(task)
        assert model == "phi3:mini"


class TestTaskDependencies:
    def test_tasks_have_dependencies(self, orchestrator):
        plan = orchestrator.plan_team("add feature")
        if len(plan.tasks) > 1:
            # First task (research) should have no dependencies
            assert plan.tasks[0].blocked_by == []
            # Implementation tasks should depend on research
            for task in plan.tasks[1:-1]:
                assert "t1" in task.blocked_by
