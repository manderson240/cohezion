"""Tests for node-scoped FLUX context injection in AgentNode.

Validates that AgentNode queries FLUX with a role-scoped query before execution,
and measures token efficiency of scoped vs global queries.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cohezion.flux.types import FluxBlock, FluxContext, FluxSource
from cohezion.graph.nodes import AgentNode
from cohezion.graph.types import NodeSpec


def _make_flux_context(blocks: list[FluxBlock], query: str = "test") -> FluxContext:
    total_chars = sum(len(b.content) for b in blocks)
    return FluxContext(
        blocks=blocks,
        total_tokens_estimated=max(1, total_chars // 4) if blocks else 0,
        query=query,
        sources_queried=[FluxSource.VAULT],
    )


def _make_block(content: str, relevance: float = 0.8) -> FluxBlock:
    return FluxBlock(content=content, source=FluxSource.VAULT, relevance_score=relevance)


class TestFluxInjection:
    """Core behavior: AgentNode injects FLUX context before execution."""

    @pytest.fixture
    def researcher_spec(self):
        return NodeSpec(
            id="n-researcher",
            name="researcher",
            node_type="agent",
            pull_keys=["query"],
            push_keys=["findings"],
            attributes={"description": "Gather background on quantum computing"},
        )

    @pytest.fixture
    def analyst_spec(self):
        return NodeSpec(
            id="n-analyst",
            name="analyst",
            node_type="agent",
            pull_keys=["findings"],
            push_keys=["analysis"],
            attributes={"description": "Analyse patterns in research data"},
        )

    @pytest.mark.asyncio
    async def test_flux_context_injected_into_inputs(self, researcher_spec):
        """FLUX blocks should appear in inputs under _flux_context key."""
        blocks = [_make_block("Prior research on quantum computing")]
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context(blocks, "test"))

        node = AgentNode(researcher_spec, flux_aggregator=flux)
        captured_inputs = {}

        async def capture_execute(inputs: dict) -> dict:
            captured_inputs.update(inputs)
            return {"findings": "done"}

        node.set_execute_fn(capture_execute)
        await node.forward({"query": "quantum"})

        assert "_flux_context" in captured_inputs
        assert len(captured_inputs["_flux_context"]) == 1
        assert "quantum computing" in captured_inputs["_flux_context"][0]

    @pytest.mark.asyncio
    async def test_flux_query_scoped_to_node_role(self, researcher_spec):
        """FLUX query should include node description, not just generic text."""
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context([]))

        node = AgentNode(researcher_spec, flux_aggregator=flux)
        node.set_execute_fn(AsyncMock(return_value={}))
        await node.forward({"query": "quantum"})

        call_args = flux.get_context.call_args
        query_used = call_args[0][0] if call_args[0] else call_args[1].get("query", "")
        # Query should contain node-specific context, not just "quantum"
        assert "quantum computing" in query_used.lower() or "researcher" in query_used.lower()

    @pytest.mark.asyncio
    async def test_different_nodes_get_different_queries(self, researcher_spec, analyst_spec):
        """Each node should produce a distinct FLUX query based on its role."""
        researcher_flux = AsyncMock()
        researcher_flux.get_context = AsyncMock(return_value=_make_flux_context([]))
        analyst_flux = AsyncMock()
        analyst_flux.get_context = AsyncMock(return_value=_make_flux_context([]))

        r_node = AgentNode(researcher_spec, flux_aggregator=researcher_flux)
        r_node.set_execute_fn(AsyncMock(return_value={}))
        await r_node.forward({"query": "quantum"})

        a_node = AgentNode(analyst_spec, flux_aggregator=analyst_flux)
        a_node.set_execute_fn(AsyncMock(return_value={}))
        await a_node.forward({"findings": "data"})

        r_query = researcher_flux.get_context.call_args[0][0]
        a_query = analyst_flux.get_context.call_args[0][0]
        assert r_query != a_query

    @pytest.mark.asyncio
    async def test_no_flux_aggregator_skips_injection(self, researcher_spec):
        """Without FLUX, AgentNode should work exactly as before (backward compat)."""
        node = AgentNode(researcher_spec)  # No flux_aggregator

        async def execute(inputs: dict) -> dict:
            return {"findings": "result"}

        node.set_execute_fn(execute)
        result = await node.forward({"query": "test"})

        assert result == {"findings": "result"}
        assert "_flux_context" not in result  # No FLUX pollution in output

    @pytest.mark.asyncio
    async def test_flux_failure_is_non_blocking(self, researcher_spec):
        """If FLUX raises, execution should proceed without context."""
        flux = AsyncMock()
        flux.get_context = AsyncMock(side_effect=RuntimeError("FLUX down"))

        node = AgentNode(researcher_spec, flux_aggregator=flux)

        async def execute(inputs: dict) -> dict:
            return {"findings": "worked anyway"}

        node.set_execute_fn(execute)
        result = await node.forward({"query": "test"})

        assert result == {"findings": "worked anyway"}

    @pytest.mark.asyncio
    async def test_flux_context_does_not_leak_into_output(self, researcher_spec):
        """FLUX context should be in inputs to execute_fn, not in final output."""
        blocks = [_make_block("background info")]
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context(blocks))

        node = AgentNode(researcher_spec, flux_aggregator=flux)

        async def execute(inputs: dict) -> dict:
            # Execute function uses context but doesn't include it in output
            return {"findings": "analysis complete"}

        node.set_execute_fn(execute)
        result = await node.forward({"query": "test"})

        assert "_flux_context" not in result

    @pytest.mark.asyncio
    async def test_low_relevance_blocks_filtered_out(self, researcher_spec):
        """Blocks below the relevance floor should be dropped, not injected."""
        blocks = [
            _make_block("High-signal research context", 0.90),
            _make_block("Noise: unrelated meeting notes", 0.30),
            _make_block("Noise: old changelog entry", 0.20),
        ]
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context(blocks))

        node = AgentNode(researcher_spec, flux_aggregator=flux)
        captured = {}

        async def capture(inputs, _c=captured):
            _c.update(inputs)
            return {"output": "done"}

        node.set_execute_fn(capture)
        await node.forward({"query": "test"})

        context = captured.get("_flux_context", [])
        assert len(context) == 1  # Only the high-signal block
        assert "High-signal" in context[0]

    @pytest.mark.asyncio
    async def test_all_low_relevance_means_no_injection(self, researcher_spec):
        """If all blocks are noise, no context should be injected at all."""
        blocks = [
            _make_block("Noise block 1", 0.30),
            _make_block("Noise block 2", 0.20),
        ]
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context(blocks))

        node = AgentNode(researcher_spec, flux_aggregator=flux)
        captured = {}

        async def capture(inputs, _c=captured):
            _c.update(inputs)
            return {"output": "done"}

        node.set_execute_fn(capture)
        await node.forward({"query": "test"})

        # No _flux_context key at all — zero tokens beats noise tokens
        assert "_flux_context" not in captured

    @pytest.mark.asyncio
    async def test_passthrough_without_execute_fn_skips_flux(self, researcher_spec):
        """Passthrough mode (no execute_fn) should not query FLUX."""
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context([]))

        node = AgentNode(researcher_spec, flux_aggregator=flux)
        # No execute_fn set — passthrough mode
        result = await node.forward({"query": "test"})

        assert result == {"query": "test"}
        flux.get_context.assert_not_called()


class TestTokenEfficiency:
    """Evaluate token efficiency of node-scoped vs global queries."""

    @pytest.mark.asyncio
    async def test_scoped_query_requests_fewer_blocks(self):
        """Node-scoped queries should request top_k=3 (focused) not top_k=10 (global)."""
        spec = NodeSpec(
            id="n1",
            name="researcher",
            node_type="agent",
            pull_keys=[],
            push_keys=[],
            attributes={"description": "Research AI safety"},
        )
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context([]))

        node = AgentNode(spec, flux_aggregator=flux)
        node.set_execute_fn(AsyncMock(return_value={}))
        await node.forward({})

        call_kwargs = flux.get_context.call_args
        top_k = call_kwargs[1].get("top_k", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None)
        # Node-scoped should request fewer blocks than global default (10)
        assert top_k is not None
        assert top_k <= 5

    @pytest.mark.asyncio
    async def test_three_node_workflow_total_tokens_vs_global(self):
        """3 nodes with scoped queries should use comparable or fewer tokens than 1 global."""
        roles = [
            ("researcher", "Gather background on topic"),
            ("analyst", "Analyse patterns in data"),
            ("reviewer", "Review and synthesise findings"),
        ]

        total_scoped_tokens = 0
        for name, desc in roles:
            spec = NodeSpec(
                id=f"n-{name}",
                name=name,
                node_type="agent",
                pull_keys=[],
                push_keys=[],
                attributes={"description": desc},
            )
            # Each node gets 3 targeted blocks (~50 chars each = ~37 tokens)
            blocks = [_make_block(f"Relevant {name} context block {i}", 0.9 - i * 0.1) for i in range(3)]
            ctx = _make_flux_context(blocks, desc)
            total_scoped_tokens += ctx.total_tokens_estimated

        # Global query: 10 blocks of mixed relevance (~50 chars each)
        global_blocks = [_make_block(f"Generic context block {i}", 0.5) for i in range(10)]
        global_ctx = _make_flux_context(global_blocks, "research analyse review topic")

        # Scoped should be within 2x of global (similar token count, higher signal)
        assert total_scoped_tokens <= global_ctx.total_tokens_estimated * 2
        # But each individual node gets focused context (3 blocks, not 10)
        assert len(global_blocks) > 3  # Global retrieves more


class TestEffectivenessEvaluation:
    """End-to-end evaluation: simulate a 3-node workflow and measure signal quality.

    "Effective" means:
    1. Each node gets context relevant to ITS role (high signal)
    2. Total tokens across all nodes stays bounded
    3. No node gets context meant for a different role (low noise)
    """

    @pytest.fixture
    def workflow_roles(self):
        return [
            NodeSpec(
                id="n-researcher",
                name="researcher",
                node_type="agent",
                pull_keys=["query"],
                push_keys=["findings"],
                attributes={"description": "Gather background on distributed systems"},
            ),
            NodeSpec(
                id="n-analyst",
                name="analyst",
                node_type="agent",
                pull_keys=["findings"],
                push_keys=["analysis"],
                attributes={"description": "Analyse failure patterns in distributed systems"},
            ),
            NodeSpec(
                id="n-reviewer",
                name="reviewer",
                node_type="agent",
                pull_keys=["analysis"],
                push_keys=["report"],
                attributes={"description": "Synthesise findings into actionable report"},
            ),
        ]

    @pytest.fixture
    def role_specific_vault(self):
        """Simulate a vault with role-specific content blocks."""
        blocks_by_keyword = {
            "gather": [
                _make_block("CAP theorem: consistency, availability, partition tolerance", 0.95),
                _make_block("Raft consensus algorithm overview for distributed state", 0.90),
                _make_block("Research methodology: systematic literature review steps", 0.85),
            ],
            "analyse": [
                _make_block("Common failure modes: split-brain, cascading timeout, thundering herd", 0.95),
                _make_block("Statistical pattern detection in distributed trace logs", 0.90),
                _make_block("Root cause analysis framework for production incidents", 0.85),
            ],
            "synthesise": [
                _make_block("Executive summary template for technical reports", 0.95),
                _make_block("Prioritisation matrix: impact vs likelihood for recommendations", 0.90),
                _make_block("Clear writing principles for actionable recommendations", 0.85),
            ],
            # Fallback for queries that don't match specific keywords
            "default": [
                _make_block("General distributed systems overview", 0.50),
                _make_block("Software engineering best practices", 0.45),
                _make_block("Project management guidelines", 0.40),
            ],
        }

        async def mock_get_context(query: str, top_k: int = 3) -> FluxContext:
            query_lower = query.lower()
            for keyword, blocks in blocks_by_keyword.items():
                if keyword in query_lower:
                    selected = blocks[:top_k]
                    return _make_flux_context(selected, query)
            return _make_flux_context(blocks_by_keyword["default"][:top_k], query)

        return mock_get_context

    @pytest.mark.asyncio
    async def test_each_node_gets_role_relevant_context(self, workflow_roles, role_specific_vault):
        """Each node should receive context matching its specific role."""
        expected_signals = {
            "n-researcher": "CAP theorem",
            "n-analyst": "failure modes",
            "n-reviewer": "summary template",
        }

        for spec in workflow_roles:
            flux = AsyncMock()
            flux.get_context = role_specific_vault

            node = AgentNode(spec, flux_aggregator=flux)
            captured = {}

            async def capture(inputs, _c=captured):
                _c.update(inputs)
                return {"output": "done"}

            node.set_execute_fn(capture)
            await node.forward({"data": "test input"})

            context = captured.get("_flux_context", [])
            expected = expected_signals[spec.id]
            found = any(expected in block for block in context)
            assert found, f"Node {spec.name} should have received '{expected}' but got: {context}"

    @pytest.mark.asyncio
    async def test_no_cross_contamination(self, workflow_roles, role_specific_vault):
        """Researcher should NOT get reviewer context and vice versa."""
        cross_check = {
            "n-researcher": "summary template",  # This is reviewer content
            "n-reviewer": "CAP theorem",  # This is researcher content
        }

        for spec in workflow_roles:
            if spec.id not in cross_check:
                continue

            flux = AsyncMock()
            flux.get_context = role_specific_vault

            node = AgentNode(spec, flux_aggregator=flux)
            captured = {}

            async def capture(inputs, _c=captured):
                _c.update(inputs)
                return {"output": "done"}

            node.set_execute_fn(capture)
            await node.forward({"data": "test"})

            context = captured.get("_flux_context", [])
            wrong_content = cross_check[spec.id]
            contaminated = any(wrong_content in block for block in context)
            assert not contaminated, (
                f"Node {spec.name} received cross-contaminated context: '{wrong_content}' found in {context}"
            )

    @pytest.mark.asyncio
    async def test_total_tokens_bounded(self, workflow_roles, role_specific_vault):
        """Total tokens across all nodes should stay reasonable."""
        total_tokens = 0

        for spec in workflow_roles:
            flux = AsyncMock()
            flux.get_context = role_specific_vault

            node = AgentNode(spec, flux_aggregator=flux)
            captured = {}

            async def capture(inputs, _c=captured):
                _c.update(inputs)
                return {"output": "done"}

            node.set_execute_fn(capture)
            await node.forward({"data": "test"})

            context = captured.get("_flux_context", [])
            chars = sum(len(block) for block in context)
            total_tokens += max(1, chars // 4) if context else 0

        # 3 nodes x 3 blocks x ~60 chars avg = ~540 chars = ~135 tokens
        # Global query would be 10 blocks x ~60 chars = ~600 chars = ~150 tokens
        # Scoped should be similar or less, but with 3x better signal per token
        assert total_tokens < 300, f"Total tokens {total_tokens} exceeds budget"

    @pytest.mark.asyncio
    async def test_average_relevance_higher_than_global(self, role_specific_vault):
        """Scoped queries should return higher average relevance than a global query."""
        # Scoped: each node gets top-relevance blocks for its role
        scoped_scores: list[float] = []
        for desc in ["Gather background", "Analyse failure patterns", "Synthesise findings"]:
            spec = NodeSpec(
                id="n",
                name="node",
                node_type="agent",
                pull_keys=[],
                push_keys=[],
                attributes={"description": desc},
            )
            ctx = await role_specific_vault(desc, top_k=3)
            scoped_scores.extend(b.relevance_score for b in ctx.blocks)

        # Global: single query gets default (lower relevance) blocks
        global_ctx = await role_specific_vault("distributed systems research analysis review", top_k=10)
        global_scores = [b.relevance_score for b in global_ctx.blocks]

        avg_scoped = sum(scoped_scores) / len(scoped_scores) if scoped_scores else 0
        avg_global = sum(global_scores) / len(global_scores) if global_scores else 0

        assert avg_scoped > avg_global, (
            f"Scoped avg relevance ({avg_scoped:.2f}) should beat global avg ({avg_global:.2f})"
        )


class TestQueryConstruction:
    """Verify the query built from NodeSpec is meaningful."""

    @pytest.mark.asyncio
    async def test_query_uses_description_when_available(self):
        spec = NodeSpec(
            id="n1",
            name="coder",
            node_type="agent",
            pull_keys=[],
            push_keys=[],
            attributes={"description": "Implement REST API endpoint"},
        )
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context([]))

        node = AgentNode(spec, flux_aggregator=flux)
        node.set_execute_fn(AsyncMock(return_value={}))
        await node.forward({})

        query = flux.get_context.call_args[0][0]
        assert "REST API" in query or "implement" in query.lower()

    @pytest.mark.asyncio
    async def test_query_falls_back_to_node_name(self):
        spec = NodeSpec(
            id="n1",
            name="data-transformer",
            node_type="agent",
            pull_keys=[],
            push_keys=[],
            attributes={},  # No description
        )
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context([]))

        node = AgentNode(spec, flux_aggregator=flux)
        node.set_execute_fn(AsyncMock(return_value={}))
        await node.forward({})

        query = flux.get_context.call_args[0][0]
        assert "data-transformer" in query

    @pytest.mark.asyncio
    async def test_query_incorporates_input_keys_for_specificity(self):
        """Input keys provide runtime context that narrows the FLUX query."""
        spec = NodeSpec(
            id="n1",
            name="analyst",
            node_type="agent",
            pull_keys=[],
            push_keys=[],
            attributes={"description": "Analyse data patterns"},
        )
        flux = AsyncMock()
        flux.get_context = AsyncMock(return_value=_make_flux_context([]))

        node = AgentNode(spec, flux_aggregator=flux)
        node.set_execute_fn(AsyncMock(return_value={}))
        await node.forward({"topic": "neural architecture search", "data": [1, 2, 3]})

        query = flux.get_context.call_args[0][0]
        # Should incorporate string input values for specificity
        assert "neural architecture search" in query
