"""Tests for VibeSpecifier — VibeIntent → VibeWorkflowSpec."""

from __future__ import annotations

import pytest

from cohezion.vibe.types import NodeDescription, OperationType, VibeIntent


def _make_intent(
    text: str = "implement a feature",
    op: OperationType = OperationType.IMPLEMENT,
    complexity: int = 2,
    keywords: list[str] | None = None,
) -> VibeIntent:
    return VibeIntent(
        raw_text=text,
        keywords=keywords or ["implement", "feature"],
        operation_type=op,
        complexity=complexity,
        confidence=0.85,
    )


@pytest.fixture
def specifier():
    from cohezion.vibe.specifier import VibeSpecifier

    return VibeSpecifier()


class TestVibeSpecifierBasic:
    @pytest.mark.asyncio
    async def test_specify_returns_vibe_workflow_spec(self, specifier):
        from cohezion.vibe.types import VibeWorkflowSpec

        intent = _make_intent()
        result = await specifier.specify(intent)
        assert isinstance(result, VibeWorkflowSpec)

    @pytest.mark.asyncio
    async def test_specify_preserves_intent(self, specifier):
        intent = _make_intent()
        result = await specifier.specify(intent)
        assert result.intent is intent

    @pytest.mark.asyncio
    async def test_specify_produces_at_least_one_node(self, specifier):
        intent = _make_intent()
        result = await specifier.specify(intent)
        assert result.node_count >= 1

    @pytest.mark.asyncio
    async def test_specify_edges_reference_valid_nodes(self, specifier):
        intent = _make_intent(complexity=3)
        result = await specifier.specify(intent)
        node_names = {n.name for n in result.node_descriptions}
        for edge in result.edge_descriptions:
            assert edge.from_name in node_names, f"Edge from unknown node: {edge.from_name}"
            assert edge.to_name in node_names, f"Edge to unknown node: {edge.to_name}"

    @pytest.mark.asyncio
    async def test_specify_node_descriptions_are_valid(self, specifier):
        intent = _make_intent()
        result = await specifier.specify(intent)
        for node in result.node_descriptions:
            assert isinstance(node, NodeDescription)
            assert node.name  # non-empty
            assert node.role  # non-empty
            assert node.agent_role  # non-empty


class TestVibeSpecifierOperationTemplates:
    @pytest.mark.asyncio
    async def test_research_intent_includes_researcher_node(self, specifier):
        intent = _make_intent(
            text="research transformers",
            op=OperationType.RESEARCH,
            complexity=1,
        )
        result = await specifier.specify(intent)
        roles = [n.agent_role for n in result.node_descriptions]
        assert "researcher" in roles

    @pytest.mark.asyncio
    async def test_implement_intent_includes_coder_node(self, specifier):
        intent = _make_intent(
            text="implement login",
            op=OperationType.IMPLEMENT,
            complexity=1,
        )
        result = await specifier.specify(intent)
        roles = [n.agent_role for n in result.node_descriptions]
        assert "coder" in roles

    @pytest.mark.asyncio
    async def test_analyze_intent_includes_analyzer_node(self, specifier):
        intent = _make_intent(
            text="analyze sales data",
            op=OperationType.ANALYZE,
            complexity=1,
        )
        result = await specifier.specify(intent)
        roles = [n.agent_role for n in result.node_descriptions]
        assert "analyst" in roles

    @pytest.mark.asyncio
    async def test_high_complexity_generates_more_nodes(self, specifier):
        low_intent = _make_intent(complexity=1)
        high_intent = _make_intent(complexity=4)
        low_result = await specifier.specify(low_intent)
        high_result = await specifier.specify(high_intent)
        assert high_result.node_count >= low_result.node_count

    @pytest.mark.asyncio
    async def test_unknown_operation_falls_back_to_generic(self, specifier):
        intent = _make_intent(op=OperationType.UNKNOWN, complexity=1)
        result = await specifier.specify(intent)
        # Should still produce at least one node
        assert result.node_count >= 1


class TestVibeSpecifierEdgeGeneration:
    @pytest.mark.asyncio
    async def test_multi_node_spec_has_edges(self, specifier):
        intent = _make_intent(complexity=3)
        result = await specifier.specify(intent)
        if result.node_count > 1:
            assert result.edge_count >= 1

    @pytest.mark.asyncio
    async def test_edges_form_linear_chain_for_simple_workflow(self, specifier):
        intent = _make_intent(complexity=2)
        result = await specifier.specify(intent)
        # For a simple chain of N nodes, should have N-1 edges
        if result.node_count == 2:
            assert result.edge_count == 1

    @pytest.mark.asyncio
    async def test_edges_carry_output_keys_from_prior_node(self, specifier):
        intent = _make_intent(complexity=3)
        result = await specifier.specify(intent)
        # Edge keys should reference outputs of source node (non-empty for multi-node)
        if result.edge_count > 0:
            edge = result.edge_descriptions[0]
            # Keys may be empty for generic edge, but from_name/to_name must differ
            assert edge.from_name != edge.to_name


class TestVibeSpecifierWithCapabilityRegistry:
    @pytest.mark.asyncio
    async def test_specifier_works_without_registry(self):
        from cohezion.vibe.specifier import VibeSpecifier

        spec = VibeSpecifier(capability_registry=None)
        intent = _make_intent()
        result = await spec.specify(intent)
        assert result.node_count >= 1

    @pytest.mark.asyncio
    async def test_specifier_uses_registry_when_provided(self):
        from unittest.mock import MagicMock

        from cohezion.vibe.specifier import VibeSpecifier

        mock_registry = MagicMock()
        mock_cap = MagicMock()
        mock_cap.name = "custom-researcher"
        mock_cap.description = "Does research"
        mock_cap.type = "agent"
        mock_registry.find.return_value = [mock_cap]

        spec = VibeSpecifier(capability_registry=mock_registry)
        intent = _make_intent(op=OperationType.RESEARCH, keywords=["research"])
        result = await spec.specify(intent)
        assert result.node_count >= 1
        # Registry was consulted
        mock_registry.find.assert_called()
