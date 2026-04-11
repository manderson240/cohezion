"""Tests for WorkflowBuilder — TeamPlan to WorkflowSpec conversion."""

from __future__ import annotations

from cohezion.graph.builder import WorkflowBuilder
from cohezion.graph.types import WorkflowSpec
from cohezion.swarm.team_orchestrator import AgentSpec, TaskSpec, TeamPlan


class TestFromTeamPlan:
    def test_simple_plan_converts(self):
        plan = TeamPlan(
            name="research",
            intent="research AI papers",
            agents=[
                AgentSpec(name="researcher", description="finds papers"),
                AgentSpec(name="writer", description="writes summary"),
            ],
            tasks=[
                TaskSpec(
                    id="t1",
                    subject="Find papers",
                    description="Search arxiv",
                    assigned_to="researcher",
                ),
                TaskSpec(
                    id="t2",
                    subject="Write summary",
                    description="Summarize",
                    assigned_to="writer",
                    blocked_by=["t1"],
                ),
            ],
        )
        builder = WorkflowBuilder()
        wf = builder.from_team_plan(plan)

        assert isinstance(wf, WorkflowSpec)
        assert len(wf.nodes) == 2
        assert len(wf.edges) == 1
        assert wf.entry_node_id == "t1"
        assert wf.exit_node_ids == ["t2"]

    def test_preserves_agent_and_task_specs(self):
        agent = AgentSpec(name="coder", description="writes code", model="opus")
        task = TaskSpec(id="t1", subject="Implement", description="Write code", assigned_to="coder")
        plan = TeamPlan(name="impl", intent="implement feature", agents=[agent], tasks=[task])

        wf = WorkflowBuilder().from_team_plan(plan)
        node = wf.get_node("t1")
        assert node is not None
        assert node.agent_spec is not None
        assert node.agent_spec.name == "coder"
        assert node.agent_spec.model == "opus"
        assert node.task_spec is not None
        assert node.task_spec.subject == "Implement"

    def test_multiple_dependencies_create_edges(self):
        plan = TeamPlan(
            name="test",
            intent="test",
            agents=[AgentSpec(name="a", description="a")],
            tasks=[
                TaskSpec(id="t1", subject="A", description="a"),
                TaskSpec(id="t2", subject="B", description="b"),
                TaskSpec(id="t3", subject="C", description="c", blocked_by=["t1", "t2"]),
            ],
        )
        wf = WorkflowBuilder().from_team_plan(plan)
        assert len(wf.edges) == 2
        preds = wf.predecessors("t3")
        assert set(preds) == {"t1", "t2"}

    def test_parallel_tasks_no_edges(self):
        plan = TeamPlan(
            name="parallel",
            intent="run in parallel",
            agents=[AgentSpec(name="a", description="a")],
            tasks=[
                TaskSpec(id="t1", subject="A", description="a"),
                TaskSpec(id="t2", subject="B", description="b"),
            ],
        )
        wf = WorkflowBuilder().from_team_plan(plan)
        assert len(wf.edges) == 0
        assert len(wf.nodes) == 2

    def test_diamond_dependency_pattern(self):
        """t1 -> (t2, t3) -> t4"""
        plan = TeamPlan(
            name="diamond",
            intent="fan out and in",
            agents=[AgentSpec(name="a", description="a")],
            tasks=[
                TaskSpec(id="t1", subject="Start", description="start"),
                TaskSpec(id="t2", subject="Branch A", description="a", blocked_by=["t1"]),
                TaskSpec(id="t3", subject="Branch B", description="b", blocked_by=["t1"]),
                TaskSpec(id="t4", subject="Merge", description="merge", blocked_by=["t2", "t3"]),
            ],
        )
        wf = WorkflowBuilder().from_team_plan(plan)
        assert len(wf.edges) == 4  # t1->t2, t1->t3, t2->t4, t3->t4
        assert wf.entry_node_id == "t1"
        assert wf.exit_node_ids == ["t4"]

    def test_entry_is_first_node_without_predecessors(self):
        plan = TeamPlan(
            name="test",
            intent="test",
            agents=[],
            tasks=[
                TaskSpec(id="t2", subject="Second", description="b", blocked_by=["t1"]),
                TaskSpec(id="t1", subject="First", description="a"),
            ],
        )
        wf = WorkflowBuilder().from_team_plan(plan)
        assert wf.entry_node_id == "t1"

    def test_exit_is_node_with_no_successors(self):
        plan = TeamPlan(
            name="test",
            intent="test",
            agents=[],
            tasks=[
                TaskSpec(id="t1", subject="A", description="a"),
                TaskSpec(id="t2", subject="B", description="b", blocked_by=["t1"]),
                TaskSpec(id="t3", subject="C", description="c", blocked_by=["t1"]),
            ],
        )
        wf = WorkflowBuilder().from_team_plan(plan)
        # Both t2 and t3 have no successors
        assert set(wf.exit_node_ids) == {"t2", "t3"}
