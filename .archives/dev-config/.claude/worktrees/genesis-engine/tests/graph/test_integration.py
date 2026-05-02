"""Integration test — TeamPlan -> WorkflowSpec -> WorkflowEngine -> result."""

from __future__ import annotations

import pytest

from cohezion.graph.builder import WorkflowBuilder
from cohezion.graph.engine import WorkflowEngine
from cohezion.graph.nodes import CustomNode
from cohezion.graph.types import NodeStatus
from cohezion.swarm.team_orchestrator import AgentSpec, TaskSpec, TeamPlan


class TestEndToEndGraphExecution:
    @pytest.mark.asyncio
    async def test_team_plan_to_graph_execution(self):
        """Build a workflow from TeamPlan, register mock nodes, execute."""
        plan = TeamPlan(
            name="research-pipeline",
            intent="research and summarize AI papers",
            agents=[
                AgentSpec(name="researcher", description="finds papers"),
                AgentSpec(name="analyzer", description="analyzes papers"),
                AgentSpec(name="writer", description="writes summary"),
            ],
            tasks=[
                TaskSpec(id="t1", subject="Find papers", description="Search arxiv", assigned_to="researcher"),
                TaskSpec(
                    id="t2",
                    subject="Analyze papers",
                    description="Extract insights",
                    assigned_to="analyzer",
                    blocked_by=["t1"],
                ),
                TaskSpec(
                    id="t3",
                    subject="Write summary",
                    description="Compile report",
                    assigned_to="writer",
                    blocked_by=["t2"],
                ),
            ],
        )

        # Build workflow from plan
        wf = WorkflowBuilder().from_team_plan(plan)
        assert len(wf.nodes) == 3
        assert len(wf.edges) == 2
        assert wf.entry_node_id == "t1"
        assert wf.exit_node_ids == ["t3"]

        # Register mock node implementations
        engine = WorkflowEngine()

        async def find_papers(inputs):
            return {"papers": ["paper1.pdf", "paper2.pdf"]}

        async def analyze(inputs):
            papers = inputs.get("papers", [])
            return {"insights": [f"insight from {p}" for p in papers]}

        async def write_summary(inputs):
            insights = inputs.get("insights", [])
            return {"summary": f"Report with {len(insights)} insights"}

        # Register nodes by task ID
        for node_spec, fn in zip(wf.nodes, [find_papers, analyze, write_summary]):
            engine.register_node(CustomNode(node_spec, forward_fn=fn))

        # Execute the workflow
        result = await engine.execute(wf, {})

        assert result.status == "completed"
        assert len(result.node_results) == 3
        assert all(nr.status == NodeStatus.COMPLETED for nr in result.node_results.values())
        assert result.final_output["summary"] == "Report with 2 insights"

    @pytest.mark.asyncio
    async def test_diamond_pattern_parallel_execution(self):
        """t1 -> (t2, t3) -> t4: verify parallel branches merge correctly."""
        plan = TeamPlan(
            name="diamond",
            intent="parallel research",
            agents=[AgentSpec(name="a", description="agent")],
            tasks=[
                TaskSpec(id="t1", subject="Start", description="init"),
                TaskSpec(id="t2", subject="Branch A", description="a", blocked_by=["t1"]),
                TaskSpec(id="t3", subject="Branch B", description="b", blocked_by=["t1"]),
                TaskSpec(id="t4", subject="Merge", description="merge", blocked_by=["t2", "t3"]),
            ],
        )

        wf = WorkflowBuilder().from_team_plan(plan)
        engine = WorkflowEngine()

        async def init_fn(inputs):
            return {"seed": 42}

        async def branch_a(inputs):
            return {"a_val": inputs.get("seed", 0) * 2}

        async def branch_b(inputs):
            return {"b_val": inputs.get("seed", 0) + 10}

        async def merge_fn(inputs):
            return {"result": inputs.get("a_val", 0) + inputs.get("b_val", 0)}

        for spec, fn in zip(wf.nodes, [init_fn, branch_a, branch_b, merge_fn]):
            engine.register_node(CustomNode(spec, forward_fn=fn))

        result = await engine.execute(wf, {})
        assert result.status == "completed"
        # 42*2 + 42+10 = 84 + 52 = 136
        assert result.final_output["result"] == 136
