"""Tests for WorkflowPersistence — SurrealDB schema and CRUD."""

from __future__ import annotations

import pytest

from cohezion.graph.persistence import WorkflowPersistence
from cohezion.graph.types import (
    EdgeSpec,
    NodeResult,
    NodeSpec,
    NodeStatus,
    WorkflowResult,
    WorkflowSpec,
)


@pytest.fixture
def persistence():
    return WorkflowPersistence()


@pytest.fixture
def sample_workflow():
    nodes = [
        NodeSpec(id="n1", name="start", node_type="agent", pull_keys=[], push_keys=["x"]),
        NodeSpec(id="n2", name="end", node_type="agent", pull_keys=["x"], push_keys=[]),
    ]
    edges = [EdgeSpec(id="e1", sender_id="n1", receiver_id="n2", keys=["x"])]
    return WorkflowSpec(
        id="wf-test-1",
        name="test-workflow",
        nodes=nodes,
        edges=edges,
        entry_node_id="n1",
        exit_node_ids=["n2"],
    )


@pytest.fixture
def sample_result():
    return WorkflowResult(
        workflow_id="wf-test-1",
        status="completed",
        node_results={
            "n1": NodeResult(
                node_id="n1",
                status=NodeStatus.COMPLETED,
                output={"x": 42},
                metrics={"tokens": 100},
                duration_ms=500,
            ),
            "n2": NodeResult(
                node_id="n2",
                status=NodeStatus.COMPLETED,
                output={"final": True},
                metrics={"tokens": 50},
                duration_ms=300,
            ),
        },
        final_output={"final": True},
        total_duration_ms=800,
        total_tokens=150,
    )


class TestWorkflowPersistence:
    def test_persist_and_retrieve_run(self, persistence, sample_workflow, sample_result):
        run_id = persistence.persist_workflow_run(sample_workflow, sample_result)
        assert run_id == "wf-test-1"

        retrieved = persistence.get_workflow_run(run_id)
        assert retrieved is not None
        assert retrieved["status"] == "completed"
        assert retrieved["total_tokens"] == 150

    def test_persist_node_results(self, persistence, sample_result):
        persistence.persist_node_results("wf-test-1", sample_result.node_results)

        nodes = persistence.get_node_results("wf-test-1")
        assert len(nodes) == 2
        assert nodes["n1"]["status"] == "completed"
        assert nodes["n1"]["output"]["x"] == 42

    def test_persist_edges(self, persistence, sample_workflow):
        persistence.persist_edges("wf-test-1", sample_workflow.edges)

        edges = persistence.get_edges("wf-test-1")
        assert len(edges) == 1
        assert edges[0]["sender_id"] == "n1"
        assert edges[0]["receiver_id"] == "n2"

    def test_get_nonexistent_run_returns_none(self, persistence):
        assert persistence.get_workflow_run("nonexistent") is None

    def test_get_surreal_schema(self, persistence):
        schema = persistence.get_schema_statements()
        assert len(schema) > 0
        assert any("workflow_node" in s for s in schema)
        assert any("workflow_edge" in s for s in schema)
        assert any("workflow_run" in s for s in schema)

    def test_list_workflow_runs(self, persistence, sample_workflow, sample_result):
        persistence.persist_workflow_run(sample_workflow, sample_result)

        # Create a second run
        wf2 = WorkflowSpec(
            id="wf-test-2",
            name="second",
            nodes=[],
            edges=[],
            entry_node_id="",
            exit_node_ids=[],
        )
        result2 = WorkflowResult(
            workflow_id="wf-test-2",
            status="failed",
            node_results={},
            final_output={},
            total_duration_ms=100,
            total_tokens=10,
        )
        persistence.persist_workflow_run(wf2, result2)

        runs = persistence.list_workflow_runs()
        assert len(runs) == 2
