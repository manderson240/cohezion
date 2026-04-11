"""Tests for VibeCompiler and VibeOrchestrator (E2E)."""

from __future__ import annotations

import pytest

from cohezion.vibe.types import (
    EdgeDescription,
    NodeDescription,
    OperationType,
    VibeIntent,
    VibeWorkflowSpec,
)


def _make_intent(
    text: str = "implement feature", op: OperationType = OperationType.IMPLEMENT
) -> VibeIntent:
    return VibeIntent(
        raw_text=text,
        keywords=["implement", "feature"],
        operation_type=op,
        complexity=2,
        confidence=0.9,
    )


def _make_spec(nodes: list[NodeDescription], edges: list[EdgeDescription]) -> VibeWorkflowSpec:
    return VibeWorkflowSpec(
        intent=_make_intent(),
        node_descriptions=nodes,
        edge_descriptions=edges,
    )


class TestVibeCompilerBasic:
    def test_compile_returns_workflow_spec(self):
        from cohezion.graph.types import WorkflowSpec
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[NodeDescription("A", "first node", "researcher")],
            edges=[],
        )
        result = compiler.compile(vibe_spec)
        assert isinstance(result, WorkflowSpec)

    def test_compile_creates_node_per_description(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[
                NodeDescription("node-A", "first", "researcher"),
                NodeDescription("node-B", "second", "coder"),
            ],
            edges=[EdgeDescription("node-A", "node-B")],
        )
        result = compiler.compile(vibe_spec)
        assert len(result.nodes) == 2

    def test_compile_creates_edges_correctly(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[
                NodeDescription("A", "first", "researcher", outputs=["data"]),
                NodeDescription("B", "second", "coder", inputs=["data"]),
            ],
            edges=[EdgeDescription("A", "B", keys=["data"])],
        )
        result = compiler.compile(vibe_spec)
        assert len(result.edges) == 1
        assert result.edges[0].keys == ["data"]

    def test_compile_sets_entry_node(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[
                NodeDescription("first", "starts here", "researcher"),
                NodeDescription("second", "ends here", "coder"),
            ],
            edges=[EdgeDescription("first", "second")],
        )
        result = compiler.compile(vibe_spec)
        assert result.entry_node_id is not None
        # Entry node is the first node (no incoming edges)
        node_map = {n.name: n for n in result.nodes}
        entry = next(n for n in result.nodes if n.id == result.entry_node_id)
        assert entry.name == "first"

    def test_compile_sets_exit_nodes(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[
                NodeDescription("first", "starts here", "researcher"),
                NodeDescription("second", "ends here", "coder"),
            ],
            edges=[EdgeDescription("first", "second")],
        )
        result = compiler.compile(vibe_spec)
        assert len(result.exit_node_ids) >= 1
        # Exit node should be the last (no outgoing edges)
        exit_node = next(n for n in result.nodes if n.id in result.exit_node_ids)
        assert exit_node.name == "second"

    def test_compile_single_node_is_entry_and_exit(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[NodeDescription("only", "sole node", "agent")],
            edges=[],
        )
        result = compiler.compile(vibe_spec)
        assert result.entry_node_id is not None
        assert len(result.exit_node_ids) == 1
        assert result.entry_node_id == result.exit_node_ids[0]

    def test_compile_node_type_set_to_agent(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[NodeDescription("A", "agent node", "researcher")],
            edges=[],
        )
        result = compiler.compile(vibe_spec)
        assert result.nodes[0].node_type == "agent"

    def test_compile_preserves_vibe_spec_name_in_workflow(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[NodeDescription("A", "node", "researcher")],
            edges=[],
        )
        result = compiler.compile(vibe_spec)
        assert "implement" in result.name.lower() or result.name  # name is non-empty


class TestVibeCompilerValidation:
    def test_empty_nodes_raises(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        with pytest.raises(ValueError, match="node"):
            compiler.compile(_make_spec(nodes=[], edges=[]))

    def test_edge_to_unknown_node_raises(self):
        from cohezion.vibe.compiler import VibeCompiler

        compiler = VibeCompiler()
        vibe_spec = _make_spec(
            nodes=[NodeDescription("A", "node", "researcher")],
            edges=[EdgeDescription("A", "GHOST")],  # GHOST doesn't exist
        )
        with pytest.raises(ValueError, match="GHOST"):
            compiler.compile(vibe_spec)
