"""Tests for WorkflowEngine — DAG validation, dispatch, and execution."""

from __future__ import annotations

import asyncio

import pytest

from cohezion.graph.engine import WorkflowEngine
from cohezion.graph.nodes import AgentNode, CustomNode, LogicSwitchNode
from cohezion.graph.types import (
    EdgeSpec,
    NodeResult,
    NodeSpec,
    NodeStatus,
    WorkflowSpec,
)


def _make_spec(
    nodes: list[NodeSpec],
    edges: list[EdgeSpec],
    entry: str | None = None,
    exits: list[str] | None = None,
) -> WorkflowSpec:
    """Helper to build a WorkflowSpec with sensible defaults."""
    return WorkflowSpec(
        id="test-wf",
        name="test",
        nodes=nodes,
        edges=edges,
        entry_node_id=entry or nodes[0].id,
        exit_node_ids=exits or [nodes[-1].id],
    )


class TestDAGValidation:
    def test_valid_dag_passes(self):
        engine = WorkflowEngine()
        nodes = [
            NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=["x"]),
            NodeSpec(id="n2", name="b", node_type="agent", pull_keys=["x"], push_keys=[]),
        ]
        edges = [EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=["x"])]
        wf = _make_spec(nodes, edges)
        errors = engine.validate_dag(wf)
        assert errors == []

    def test_detects_cycle(self):
        engine = WorkflowEngine()
        nodes = [
            NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=[]),
            NodeSpec(id="n2", name="b", node_type="agent", pull_keys=[], push_keys=[]),
        ]
        edges = [
            EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=[]),
            EdgeSpec(id="e2", sender_id="n2", receiver_id="n1", keys=[]),
        ]
        wf = _make_spec(nodes, edges)
        errors = engine.validate_dag(wf)
        assert any("cycle" in e.lower() for e in errors)

    def test_detects_missing_entry_node(self):
        engine = WorkflowEngine()
        nodes = [NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=[])]
        wf = _make_spec(nodes, [], entry="missing")
        errors = engine.validate_dag(wf)
        assert any("entry" in e.lower() for e in errors)

    def test_detects_missing_exit_node(self):
        engine = WorkflowEngine()
        nodes = [NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=[])]
        wf = _make_spec(nodes, [], exits=["missing"])
        errors = engine.validate_dag(wf)
        assert any("exit" in e.lower() for e in errors)

    def test_detects_edge_with_missing_node(self):
        engine = WorkflowEngine()
        nodes = [NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=[])]
        edges = [EdgeSpec(id="e1", sender_id="n1", receiver_id="ghost", keys=[])]
        wf = _make_spec(nodes, edges, exits=["n1"])
        errors = engine.validate_dag(wf)
        assert any("ghost" in e for e in errors)


class TestWorkflowExecution:
    @pytest.mark.asyncio
    async def test_single_node_workflow(self):
        engine = WorkflowEngine()
        spec = NodeSpec(id="n1", name="echo", node_type="custom", pull_keys=["msg"], push_keys=["out"])
        wf = _make_spec([spec], [], entry="n1", exits=["n1"])

        async def echo(inputs):
            return {"out": f"echo: {inputs.get('msg', '')}"}

        node = CustomNode(spec, forward_fn=echo)
        engine.register_node(node)

        result = await engine.execute(wf, {"msg": "hello"})
        assert result.status == "completed"
        assert result.node_results["n1"].status == NodeStatus.COMPLETED
        assert result.final_output["out"] == "echo: hello"

    @pytest.mark.asyncio
    async def test_linear_chain(self):
        """n1 -> n2 -> n3: each doubles the value."""
        engine = WorkflowEngine()
        nodes = [
            NodeSpec(id="n1", name="a", node_type="custom", pull_keys=["val"], push_keys=["val"]),
            NodeSpec(id="n2", name="b", node_type="custom", pull_keys=["val"], push_keys=["val"]),
            NodeSpec(id="n3", name="c", node_type="custom", pull_keys=["val"], push_keys=["val"]),
        ]
        edges = [
            EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=["val"]),
            EdgeSpec(id="e2", sender_id="n2", receiver_id="n3", keys=["val"]),
        ]
        wf = _make_spec(nodes, edges)

        for spec in nodes:
            async def doubler(inputs, _s=spec):
                return {"val": inputs.get("val", 0) * 2}
            engine.register_node(CustomNode(spec, forward_fn=doubler))

        result = await engine.execute(wf, {"val": 1})
        assert result.status == "completed"
        # 1 -> 2 -> 4 -> 8
        assert result.final_output["val"] == 8

    @pytest.mark.asyncio
    async def test_parallel_fan_out_fan_in(self):
        """n1 -> (n2, n3) -> n4: n2 and n3 run in parallel."""
        engine = WorkflowEngine()
        execution_order = []

        nodes = [
            NodeSpec(id="n1", name="start", node_type="custom", pull_keys=[], push_keys=["data"]),
            NodeSpec(id="n2", name="branch_a", node_type="custom", pull_keys=["data"], push_keys=["a_result"]),
            NodeSpec(id="n3", name="branch_b", node_type="custom", pull_keys=["data"], push_keys=["b_result"]),
            NodeSpec(id="n4", name="merge", node_type="custom", pull_keys=["a_result", "b_result"], push_keys=["final"]),
        ]
        edges = [
            EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=["data"]),
            EdgeSpec(id="e2", sender_id="n1", receiver_id="n3", keys=["data"]),
            EdgeSpec(id="e3", sender_id="n2", receiver_id="n4", keys=["a_result"]),
            EdgeSpec(id="e4", sender_id="n3", receiver_id="n4", keys=["b_result"]),
        ]
        wf = _make_spec(nodes, edges, exits=["n4"])

        async def start_fn(inputs):
            execution_order.append("n1")
            return {"data": "payload"}

        async def branch_a(inputs):
            execution_order.append("n2")
            return {"a_result": f"A({inputs.get('data', '')})"}

        async def branch_b(inputs):
            execution_order.append("n3")
            return {"b_result": f"B({inputs.get('data', '')})"}

        async def merge_fn(inputs):
            execution_order.append("n4")
            return {"final": f"{inputs.get('a_result', '')}+{inputs.get('b_result', '')}"}

        engine.register_node(CustomNode(nodes[0], forward_fn=start_fn))
        engine.register_node(CustomNode(nodes[1], forward_fn=branch_a))
        engine.register_node(CustomNode(nodes[2], forward_fn=branch_b))
        engine.register_node(CustomNode(nodes[3], forward_fn=merge_fn))

        result = await engine.execute(wf, {})
        assert result.status == "completed"
        # n1 must be first, n4 must be last, n2/n3 in between
        assert execution_order[0] == "n1"
        assert execution_order[-1] == "n4"
        assert set(execution_order[1:3]) == {"n2", "n3"}
        assert result.final_output["final"] == "A(payload)+B(payload)"

    @pytest.mark.asyncio
    async def test_node_failure_marks_workflow_failed(self):
        engine = WorkflowEngine()
        spec = NodeSpec(id="n1", name="fail", node_type="custom", pull_keys=[], push_keys=[])
        wf = _make_spec([spec], [], exits=["n1"])

        async def fail_fn(inputs):
            raise ValueError("Intentional failure")

        engine.register_node(CustomNode(spec, forward_fn=fail_fn))
        result = await engine.execute(wf, {})
        assert result.status == "failed"
        assert result.node_results["n1"].status == NodeStatus.FAILED
        assert "Intentional failure" in (result.node_results["n1"].error or "")

    @pytest.mark.asyncio
    async def test_downstream_nodes_skipped_after_failure(self):
        engine = WorkflowEngine()
        nodes = [
            NodeSpec(id="n1", name="fail", node_type="custom", pull_keys=[], push_keys=[]),
            NodeSpec(id="n2", name="skip", node_type="custom", pull_keys=[], push_keys=[]),
        ]
        edges = [EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=[])]
        wf = _make_spec(nodes, edges)

        async def fail_fn(inputs):
            raise RuntimeError("boom")

        engine.register_node(CustomNode(nodes[0], forward_fn=fail_fn))
        engine.register_node(CustomNode(nodes[1]))

        result = await engine.execute(wf, {})
        assert result.node_results["n1"].status == NodeStatus.FAILED
        assert result.node_results["n2"].status == NodeStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_empty_workflow_with_no_edges(self):
        engine = WorkflowEngine()
        spec = NodeSpec(id="n1", name="solo", node_type="custom", pull_keys=[], push_keys=["out"])
        wf = _make_spec([spec], [], exits=["n1"])

        async def solo_fn(inputs):
            return {"out": "done"}

        engine.register_node(CustomNode(spec, forward_fn=solo_fn))
        result = await engine.execute(wf, {})
        assert result.status == "completed"
