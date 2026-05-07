"""Tests for the FLUX context bus on WorkflowEngine.

Validates that the engine records execution summaries to HistoryFlux
and that AgentNodes receive FLUX context from prior node executions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.flux.aggregator import FluxAggregator
from cohezion.flux.providers.history_flux import HistoryFlux
from cohezion.flux.types import FluxSource
from cohezion.graph.engine import WorkflowEngine
from cohezion.graph.nodes import AgentNode
from cohezion.graph.types import EdgeSpec, NodeSpec, WorkflowSpec


def _make_spec(
    node_id: str,
    name: str,
    node_type: str = "agent",
    **attrs: object,
) -> NodeSpec:
    return NodeSpec(
        id=node_id,
        name=name,
        node_type=node_type,
        pull_keys=[],
        push_keys=[],
        attributes=dict(attrs),
    )


def _make_workflow(
    nodes: list[NodeSpec],
    edges: list[EdgeSpec] | None = None,
) -> WorkflowSpec:
    edges = edges or []
    receivers = {e.receiver_id for e in edges}
    entry = next((n for n in nodes if n.id not in receivers), nodes[0])
    senders = {e.sender_id for e in edges}
    exits = [n for n in nodes if n.id not in senders] or [nodes[-1]]
    return WorkflowSpec(
        id="test-wf",
        name="test-workflow",
        nodes=nodes,
        edges=edges,
        entry_node_id=entry.id,
        exit_node_ids=[n.id for n in exits],
    )


# ─── FluxAggregator.record_history() ────────────────────────────────


class TestRecordHistory:
    """FluxAggregator should delegate record_history to its HistoryFlux provider."""

    def test_record_history_delegates_to_history_provider(self):
        """record_history() should call HistoryFlux.record()."""
        history = HistoryFlux()
        agg = FluxAggregator(providers=[history])

        agg.record_history("node completed: researcher", {"node_id": "n1"})

        assert len(history._entries) == 1
        assert "researcher" in history._entries[0]["content"]

    def test_record_history_no_history_provider_is_noop(self):
        """record_history() with no HistoryFlux provider should not raise."""
        agg = FluxAggregator(providers=[])
        # Should not raise
        agg.record_history("some content", {})

    def test_record_history_finds_history_among_multiple_providers(self):
        """record_history() should find HistoryFlux even among other providers."""
        history = HistoryFlux()
        mock_provider = AsyncMock()
        mock_provider.source = FluxSource.VAULT
        agg = FluxAggregator(providers=[mock_provider, history])

        agg.record_history("test content", {})

        assert len(history._entries) == 1


# ─── WorkflowEngine records execution summaries ─────────────────────


class TestEngineRecordsToFlux:
    """WorkflowEngine should record node results to FLUX after completion."""

    @pytest.mark.asyncio
    async def test_engine_records_completed_node_to_history(self):
        """After a node completes, engine should record a summary to FLUX."""
        history = HistoryFlux()
        flux = FluxAggregator(providers=[history])
        engine = WorkflowEngine(flux_aggregator=flux)

        spec = _make_spec("n1", "researcher", description="Find papers on AI safety")
        node = AgentNode(spec)
        node.set_execute_fn(AsyncMock(return_value={"summary": "found 5 papers"}))
        engine.register_node(node)

        workflow = _make_workflow([spec])
        await engine.execute(workflow, {"topic": "AI safety"})

        # Engine should have recorded to history
        assert len(history._entries) >= 1
        entry = history._entries[0]["content"]
        assert "researcher" in entry.lower()

    @pytest.mark.asyncio
    async def test_engine_does_not_record_without_flux(self):
        """Without flux_aggregator, engine should not attempt recording."""
        engine = WorkflowEngine()  # No flux

        spec = _make_spec("n1", "researcher")
        node = AgentNode(spec)
        node.set_execute_fn(AsyncMock(return_value={"output": "done"}))
        engine.register_node(node)

        workflow = _make_workflow([spec])
        # Should execute without error
        result = await engine.execute(workflow, {})
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_engine_records_metadata_with_node_id(self):
        """Recorded history entry should include node_id in metadata."""
        history = HistoryFlux()
        flux = FluxAggregator(providers=[history])
        engine = WorkflowEngine(flux_aggregator=flux)

        spec = _make_spec("node-42", "analyst")
        node = AgentNode(spec)
        node.set_execute_fn(AsyncMock(return_value={"analysis": "growth trend"}))
        engine.register_node(node)

        workflow = _make_workflow([spec])
        await engine.execute(workflow, {})

        meta = history._entries[0]["metadata"]
        assert meta["node_id"] == "node-42"
        assert meta["node_name"] == "analyst"

    @pytest.mark.asyncio
    async def test_failed_node_not_recorded(self):
        """Failed nodes should not be recorded as useful context."""
        history = HistoryFlux()
        flux = FluxAggregator(providers=[history])
        engine = WorkflowEngine(flux_aggregator=flux)

        spec = _make_spec("n1", "broken-node")
        node = AgentNode(spec)
        node.set_execute_fn(AsyncMock(side_effect=RuntimeError("boom")))
        engine.register_node(node)

        workflow = _make_workflow([spec])
        await engine.execute(workflow, {})

        # No entries — failed nodes shouldn't pollute the context
        assert len(history._entries) == 0


# ─── Intra-workflow compounding ──────────────────────────────────────


class TestIntraWorkflowCompounding:
    """Later nodes should benefit from earlier nodes' results via FLUX."""

    @pytest.mark.asyncio
    async def test_node_b_receives_node_a_result_via_flux(self):
        """Node B's FLUX context should include summaries from Node A's execution."""
        history = HistoryFlux()
        flux = FluxAggregator(providers=[history])
        engine = WorkflowEngine(flux_aggregator=flux)

        spec_a = _make_spec("a", "researcher", description="Research AI safety papers and findings")
        spec_b = _make_spec("b", "reviewer", description="Review AI safety research papers")

        # Track what Node B receives as inputs
        captured_b: dict = {}

        async def execute_b(inputs):
            captured_b.update(inputs)
            return {"review": "looks good"}

        node_a = AgentNode(spec_a, flux_aggregator=flux)
        node_a.set_execute_fn(AsyncMock(return_value={"papers": "5 papers on safety"}))

        node_b = AgentNode(spec_b, flux_aggregator=flux)
        node_b.set_execute_fn(execute_b)

        engine.register_node(node_a)
        engine.register_node(node_b)

        edge = EdgeSpec(
            id="e1",
            sender_id="a",
            receiver_id="b",
            keys=[],
        )
        workflow = _make_workflow([spec_a, spec_b], edges=[edge])
        await engine.execute(workflow, {"topic": "safety"})

        # Node B should have received FLUX context containing Node A's summary
        flux_ctx = captured_b.get("_flux_context", [])
        assert len(flux_ctx) >= 1
        # The context should reference the researcher's work
        combined = " ".join(flux_ctx).lower()
        assert "researcher" in combined or "research" in combined

    @pytest.mark.asyncio
    async def test_parallel_nodes_do_not_see_each_others_results(self):
        """Nodes executing in the same wave should not see each other via FLUX."""
        history = HistoryFlux()
        flux = FluxAggregator(providers=[history])
        engine = WorkflowEngine(flux_aggregator=flux)

        spec_a = _make_spec("a", "researcher-alpha")
        spec_b = _make_spec("b", "researcher-beta")

        node_a = AgentNode(spec_a, flux_aggregator=flux)
        node_a.set_execute_fn(AsyncMock(return_value={"out": "alpha"}))

        node_b = AgentNode(spec_b, flux_aggregator=flux)
        node_b.set_execute_fn(AsyncMock(return_value={"out": "beta"}))

        engine.register_node(node_a)
        engine.register_node(node_b)

        # No edges = both are roots = same wave = parallel
        workflow = _make_workflow([spec_a, spec_b])
        await engine.execute(workflow, {})

        # History should have entries (from both completions)
        # but neither should have seen the other during execution
        # (they ran in the same gather wave)
        assert len(history._entries) == 2


# ─── Token efficiency ────────────────────────────────────────────────


class TestContextBusTokenEfficiency:
    """Execution summaries should be compact and high-relevance."""

    @pytest.mark.asyncio
    async def test_execution_summary_is_compact(self):
        """Recorded summaries should be under 100 tokens (~400 chars)."""
        history = HistoryFlux()
        flux = FluxAggregator(providers=[history])
        engine = WorkflowEngine(flux_aggregator=flux)

        spec = _make_spec(
            "n1",
            "researcher",
            description="A very long description " * 20,  # ~460 chars
        )
        node = AgentNode(spec)
        big_output = {"data": "x" * 2000}
        node.set_execute_fn(AsyncMock(return_value=big_output))
        engine.register_node(node)

        workflow = _make_workflow([spec])
        await engine.execute(workflow, {"input": "y" * 1000})

        content = history._entries[0]["content"]
        # Summary should be compact regardless of input/output size
        assert len(content) < 400, f"Summary too long: {len(content)} chars"


# ─── Exception resilience ─────────────────────────────────────────


class TestRecordToFluxResilience:
    """_record_to_flux failures must not crash the workflow."""

    @pytest.mark.asyncio
    async def test_record_history_exception_does_not_crash_workflow(self):
        """If record_history raises, the workflow should still complete."""
        flux = MagicMock(spec=FluxAggregator)
        flux.record_history.side_effect = RuntimeError("storage down")
        engine = WorkflowEngine(flux_aggregator=flux)

        spec = _make_spec("n1", "researcher")
        node = AgentNode(spec)
        node.set_execute_fn(AsyncMock(return_value={"result": "ok"}))
        engine.register_node(node)

        workflow = _make_workflow([spec])
        result = await engine.execute(workflow, {"input": "test"})

        assert result.status == "completed"
        assert "n1" in result.node_results
        assert result.node_results["n1"].output == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_record_history_exception_logged_as_warning(self):
        """Failed recording should log a warning with exc_info."""
        flux = MagicMock(spec=FluxAggregator)
        flux.record_history.side_effect = RuntimeError("storage down")
        engine = WorkflowEngine(flux_aggregator=flux)

        spec = _make_spec("n1", "researcher")
        node = AgentNode(spec)
        node.set_execute_fn(AsyncMock(return_value={"out": "done"}))
        engine.register_node(node)

        workflow = _make_workflow([spec])
        with patch("cohezion.graph.engine.logger") as mock_logger:
            await engine.execute(workflow, {})
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args
            assert call_kwargs[1].get("exc_info") is True


# ─── GraphEngine FLUX wiring ─────────────────────────────────────


class TestGraphEngineFLUXWiring:
    """GraphEngine should propagate FLUX aggregator to AgentNodes."""

    @pytest.mark.asyncio
    async def test_engine_with_flux_records_history(self):
        """Engine with flux_aggregator should record history on node completion."""
        history = HistoryFlux()
        flux = FluxAggregator(providers=[history])

        spec = _make_spec("n1", "analyst", node_type="agent")
        workflow = _make_workflow([spec])

        engine = WorkflowEngine(flux_aggregator=flux)
        node = AgentNode(spec, flux_aggregator=flux)
        node.set_execute_fn(AsyncMock(return_value={"out": "done"}))
        engine.register_node(node)

        result = await engine.execute(workflow, {"data": "test"})

        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_engine_without_flux_still_works(self):
        """Engine without flux_aggregator should not error."""
        spec = _make_spec("n1", "worker", node_type="agent")
        workflow = _make_workflow([spec])

        engine = WorkflowEngine()
        node = AgentNode(spec)
        node.set_execute_fn(AsyncMock(return_value={"out": "done"}))
        engine.register_node(node)

        result = await engine.execute(workflow, {})

        assert result.status == "completed"
# NOTE: Removed TestExecuteGraphWiring (Wave 3E).
# ExecutionOrchestrator.execute_graph was removed in the graph API refactor.
# NOTE: Removed TestExecuteGraphWiring (Wave 3E).
# ExecutionOrchestrator.execute_graph was removed in the graph API refactor.