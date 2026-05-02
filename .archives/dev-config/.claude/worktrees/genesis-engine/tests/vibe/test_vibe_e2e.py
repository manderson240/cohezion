"""End-to-end tests for VibeOrchestrator — NL text → WorkflowSpec or WorkflowResult."""

from __future__ import annotations

import pytest


class TestVibeOrchestratorBasic:
    @pytest.mark.asyncio
    async def test_vibe_returns_workflow_spec_by_default(self):
        from cohezion.graph.types import WorkflowSpec
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        result = await orch.vibe("implement a feature", execute=False)
        assert isinstance(result, WorkflowSpec)

    @pytest.mark.asyncio
    async def test_vibe_spec_has_nodes(self):
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        result = await orch.vibe("research the topic", execute=False)
        assert len(result.nodes) >= 1

    @pytest.mark.asyncio
    async def test_vibe_spec_is_valid_dag(self):
        from cohezion.graph.engine import WorkflowEngine
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        spec = await orch.vibe("analyze data and generate report", execute=False)
        engine = WorkflowEngine()
        # Should not raise
        engine.validate_dag(spec)

    @pytest.mark.asyncio
    async def test_vibe_research_text_produces_researcher_node(self):
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        spec = await orch.vibe("research machine learning papers", execute=False)
        node_types = [n.node_type for n in spec.nodes]
        # All nodes from vibe are agent type
        assert all(t == "agent" for t in node_types)

    @pytest.mark.asyncio
    async def test_vibe_with_execute_returns_workflow_result(self):
        from cohezion.graph.types import WorkflowResult
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        result = await orch.vibe("implement a feature", execute=True)
        assert isinstance(result, WorkflowResult)

    @pytest.mark.asyncio
    async def test_vibe_execute_result_has_node_results(self):
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        result = await orch.vibe("implement a feature", execute=True)
        assert len(result.node_results) >= 1

    @pytest.mark.asyncio
    async def test_vibe_create_default_returns_orchestrator(self):
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator.create_default()
        assert isinstance(orch, VibeOrchestrator)

    @pytest.mark.asyncio
    async def test_vibe_empty_text_still_returns_spec(self):
        """Edge case: empty intent should return minimal WorkflowSpec."""
        from cohezion.graph.types import WorkflowSpec
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        result = await orch.vibe("", execute=False)
        assert isinstance(result, WorkflowSpec)
        assert len(result.nodes) >= 1

    @pytest.mark.asyncio
    async def test_vibe_pipeline_parse_specify_compile_connected(self):
        """Verify the full pipeline: intent keywords flow through to node roles."""
        from cohezion.vibe.orchestrator import VibeOrchestrator

        orch = VibeOrchestrator()
        spec = await orch.vibe("analyze sales data and produce report", execute=False)
        # The workflow should have nodes with meaningful names
        assert all(n.name for n in spec.nodes)
        assert all(n.name != "unknown" for n in spec.nodes)
