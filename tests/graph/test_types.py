"""Tests for graph type definitions — NodeSpec, EdgeSpec, WorkflowSpec, etc."""

from __future__ import annotations

import pytest

from cohezion.graph.types import (
    EdgeSpec,
    NodeResult,
    NodeSpec,
    NodeStatus,
    WorkflowResult,
    WorkflowSpec,
)


class TestNodeSpec:
    def test_create_agent_node(self):
        node = NodeSpec(
            id="agent-1",
            name="researcher",
            node_type="agent",
            pull_keys=["query"],
            push_keys=["findings"],
        )
        assert node.id == "agent-1"
        assert node.node_type == "agent"
        assert node.pull_keys == ["query"]
        assert node.push_keys == ["findings"]
        assert node.attributes == {}
        assert node.agent_spec is None

    def test_create_with_attributes(self):
        node = NodeSpec(
            id="tool-1",
            name="search",
            node_type="tool",
            pull_keys=["input"],
            push_keys=["output"],
            attributes={"timeout_ms": 5000},
        )
        assert node.attributes["timeout_ms"] == 5000

    def test_create_logic_switch(self):
        node = NodeSpec(
            id="switch-1",
            name="route",
            node_type="logic_switch",
            pull_keys=["result"],
            push_keys=["decision"],
        )
        assert node.node_type == "logic_switch"

    def test_to_dict_roundtrip(self):
        node = NodeSpec(
            id="n1",
            name="test",
            node_type="agent",
            pull_keys=["a"],
            push_keys=["b"],
            attributes={"key": "value"},
        )
        d = node.to_dict()
        assert d["id"] == "n1"
        assert d["node_type"] == "agent"
        restored = NodeSpec.from_dict(d)
        assert restored.id == node.id
        assert restored.attributes == node.attributes


class TestEdgeSpec:
    def test_create_edge(self):
        edge = EdgeSpec(
            id="e1",
            sender_id="node-a",
            receiver_id="node-b",
            keys=["findings"],
        )
        assert edge.sender_id == "node-a"
        assert edge.receiver_id == "node-b"
        assert edge.condition is None
        assert edge.weight == 1.0

    def test_conditional_edge(self):
        edge = EdgeSpec(
            id="e2",
            sender_id="switch-1",
            receiver_id="handler-a",
            keys=["result"],
            condition="decision == 'approve'",
            weight=0.8,
        )
        assert edge.condition == "decision == 'approve'"
        assert edge.weight == 0.8

    def test_to_dict_roundtrip(self):
        edge = EdgeSpec(
            id="e1",
            sender_id="a",
            receiver_id="b",
            keys=["x"],
            condition="x > 0",
            weight=0.5,
        )
        d = edge.to_dict()
        restored = EdgeSpec.from_dict(d)
        assert restored.condition == edge.condition
        assert restored.weight == edge.weight


class TestWorkflowSpec:
    def test_create_simple_workflow(self):
        nodes = [
            NodeSpec(id="n1", name="start", node_type="agent", pull_keys=[], push_keys=["data"]),
            NodeSpec(id="n2", name="end", node_type="agent", pull_keys=["data"], push_keys=[]),
        ]
        edges = [
            EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=["data"]),
        ]
        wf = WorkflowSpec(
            id="wf-1",
            name="simple",
            nodes=nodes,
            edges=edges,
            entry_node_id="n1",
            exit_node_ids=["n2"],
        )
        assert len(wf.nodes) == 2
        assert len(wf.edges) == 1
        assert wf.entry_node_id == "n1"

    def test_node_lookup(self):
        nodes = [
            NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=[]),
            NodeSpec(id="n2", name="b", node_type="tool", pull_keys=[], push_keys=[]),
        ]
        wf = WorkflowSpec(
            id="wf-1", name="test", nodes=nodes, edges=[],
            entry_node_id="n1", exit_node_ids=["n2"],
        )
        assert wf.get_node("n1").name == "a"
        assert wf.get_node("n2").node_type == "tool"
        assert wf.get_node("missing") is None

    def test_adjacency_list(self):
        nodes = [
            NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=["x"]),
            NodeSpec(id="n2", name="b", node_type="agent", pull_keys=["x"], push_keys=["y"]),
            NodeSpec(id="n3", name="c", node_type="agent", pull_keys=["y"], push_keys=[]),
        ]
        edges = [
            EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=["x"]),
            EdgeSpec(id="e2", sender_id="n2", receiver_id="n3", keys=["y"]),
        ]
        wf = WorkflowSpec(
            id="wf-1", name="chain", nodes=nodes, edges=edges,
            entry_node_id="n1", exit_node_ids=["n3"],
        )
        adj = wf.adjacency_list()
        assert adj["n1"] == ["n2"]
        assert adj["n2"] == ["n3"]
        assert adj["n3"] == []

    def test_predecessors(self):
        nodes = [
            NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=[]),
            NodeSpec(id="n2", name="b", node_type="agent", pull_keys=[], push_keys=[]),
            NodeSpec(id="n3", name="c", node_type="agent", pull_keys=[], push_keys=[]),
        ]
        edges = [
            EdgeSpec(id="e1", sender_id="n1", receiver_id="n3", keys=[]),
            EdgeSpec(id="e2", sender_id="n2", receiver_id="n3", keys=[]),
        ]
        wf = WorkflowSpec(
            id="wf-1", name="fan-in", nodes=nodes, edges=edges,
            entry_node_id="n1", exit_node_ids=["n3"],
        )
        preds = wf.predecessors("n3")
        assert set(preds) == {"n1", "n2"}
        assert wf.predecessors("n1") == []

    def test_to_dict_roundtrip(self):
        nodes = [
            NodeSpec(id="n1", name="a", node_type="agent", pull_keys=[], push_keys=["x"]),
            NodeSpec(id="n2", name="b", node_type="tool", pull_keys=["x"], push_keys=[]),
        ]
        edges = [EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=["x"])]
        wf = WorkflowSpec(
            id="wf-1", name="test", nodes=nodes, edges=edges,
            entry_node_id="n1", exit_node_ids=["n2"],
        )
        d = wf.to_dict()
        restored = WorkflowSpec.from_dict(d)
        assert restored.id == wf.id
        assert len(restored.nodes) == 2
        assert len(restored.edges) == 1


class TestNodeStatus:
    def test_enum_values(self):
        assert NodeStatus.PENDING.value == "pending"
        assert NodeStatus.READY.value == "ready"
        assert NodeStatus.RUNNING.value == "running"
        assert NodeStatus.COMPLETED.value == "completed"
        assert NodeStatus.FAILED.value == "failed"
        assert NodeStatus.SKIPPED.value == "skipped"


class TestNodeResult:
    def test_successful_result(self):
        result = NodeResult(
            node_id="n1",
            status=NodeStatus.COMPLETED,
            output={"findings": "important data"},
            metrics={"tokens": 150},
            duration_ms=1200.5,
        )
        assert result.error is None
        assert result.output["findings"] == "important data"

    def test_failed_result(self):
        result = NodeResult(
            node_id="n1",
            status=NodeStatus.FAILED,
            output={},
            metrics={},
            duration_ms=50.0,
            error="Model timeout",
        )
        assert result.error == "Model timeout"


class TestWorkflowResult:
    def test_workflow_result(self):
        node_results = {
            "n1": NodeResult(
                node_id="n1", status=NodeStatus.COMPLETED,
                output={"x": 1}, metrics={}, duration_ms=100,
            ),
            "n2": NodeResult(
                node_id="n2", status=NodeStatus.COMPLETED,
                output={"y": 2}, metrics={}, duration_ms=200,
            ),
        }
        result = WorkflowResult(
            workflow_id="wf-1",
            status="completed",
            node_results=node_results,
            final_output={"y": 2},
            total_duration_ms=300,
            total_tokens=500,
        )
        assert result.status == "completed"
        assert len(result.node_results) == 2
        assert result.total_tokens == 500
