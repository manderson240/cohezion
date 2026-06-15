"""Tests for HyperedgePattern extensions — Hyper-Extract concepts.

Note on API: ``HyperedgePattern`` and ``ingest_execution_trace`` already existed
before this sprint with a ``step_names / domains / relation`` signature.  The
new additive additions tested here are:

- ``MyceliumRegistry.get_hyperedge_patterns(min_weight)`` — weight-filtered read
- ``MyceliumRegistry.ingest_agent_tool_trace(agents, tools, outcome, metadata)``
  — Hyper-Extract-flavoured entry point that maps to the existing storage model

Existing ``TestHyperedgePattern`` tests in test_mycelium_registry.py cover the
core ``ingest_execution_trace`` contract and are NOT duplicated here.
"""

from __future__ import annotations

from cohezion.learning.mycelium_registry import HyperedgePattern, MyceliumRegistry


class TestIngestAgentToolTrace:
    """test_ingest_creates_pattern — basic happy path via ingest_agent_tool_trace."""

    def test_ingest_creates_pattern(self) -> None:
        """Ingesting agents + tools + outcome produces a HyperedgePattern."""
        registry = MyceliumRegistry()
        result = registry.ingest_agent_tool_trace(
            agents=["planner", "executor"],
            tools=["file_read"],
            outcome="success",
        )
        assert isinstance(result, HyperedgePattern)
        # nodes are sorted union of agents + tools
        assert set(result.nodes) == {"planner", "executor", "file_read"}
        assert result.weight == 1.0
        assert len(registry.hyperedges) == 1

    def test_deduplication_increments_weight(self) -> None:
        """Same agent+tool set with same outcome increments weight, not count."""
        registry = MyceliumRegistry()
        registry.ingest_agent_tool_trace(
            agents=["planner"],
            tools=["surreal_query"],
            outcome="success",
        )
        registry.ingest_agent_tool_trace(
            # Order differs — frozenset dedup must still match
            agents=["planner"],
            tools=["surreal_query"],
            outcome="success",
        )
        assert len(registry.hyperedges) == 1
        assert registry.hyperedges[0].weight == 2.0

    def test_different_relations_separate_patterns(self) -> None:
        """Different outcome strings produce separate hyperedge entries."""
        registry = MyceliumRegistry()
        registry.ingest_agent_tool_trace(
            agents=["act"],
            tools=["file_write"],
            outcome="co-execution",
        )
        registry.ingest_agent_tool_trace(
            agents=["act"],
            tools=["file_write"],
            outcome="data-flow",
        )
        assert len(registry.hyperedges) == 2

    def test_min_weight_filter(self) -> None:
        """get_hyperedge_patterns(min_weight) filters by occurrence weight."""
        registry = MyceliumRegistry()
        # Ingest pattern A three times (weight=3) and pattern B once (weight=1)
        for _ in range(3):
            registry.ingest_agent_tool_trace(
                agents=["checker"],
                tools=["lint"],
                outcome="pass",
            )
        registry.ingest_agent_tool_trace(
            agents=["reporter"],
            tools=["notify"],
            outcome="alert",
        )
        above_two = registry.get_hyperedge_patterns(min_weight=2.0)
        assert len(above_two) == 1
        assert above_two[0].weight == 3.0

        all_patterns = registry.get_hyperedge_patterns(min_weight=0.01)
        assert len(all_patterns) == 2

    def test_ingest_empty_agents(self) -> None:
        """Empty agents list is handled gracefully — no crash, pattern returned."""
        registry = MyceliumRegistry()
        result = registry.ingest_agent_tool_trace(
            agents=[],
            tools=["some_tool"],
            outcome="partial",
        )
        assert isinstance(result, HyperedgePattern)
        # Must not raise; weight starts at 1
        assert result.weight >= 1.0

    def test_metadata_task_type_captured_as_domain(self) -> None:
        """task_type from metadata appears in the pattern's source_domains."""
        registry = MyceliumRegistry()
        result = registry.ingest_agent_tool_trace(
            agents=["planner"],
            tools=["db_query"],
            outcome="success",
            metadata={"task_type": "reasoning", "latency_ms": 42},
        )
        assert "reasoning" in result.source_domains

    def test_metadata_none_does_not_crash(self) -> None:
        """metadata=None is treated as no-op — pattern still created."""
        registry = MyceliumRegistry()
        result = registry.ingest_agent_tool_trace(
            agents=["act"],
            tools=[],
            outcome="done",
            metadata=None,
        )
        assert isinstance(result, HyperedgePattern)


class TestGetHyperedgePatterns:
    """Direct tests for the new get_hyperedge_patterns method."""

    def test_returns_empty_list_when_no_patterns(self) -> None:
        """Registry with no ingested traces returns empty list."""
        registry = MyceliumRegistry()
        assert registry.get_hyperedge_patterns() == []

    def test_default_min_weight_returns_all(self) -> None:
        """Default min_weight=0.01 returns all patterns."""
        registry = MyceliumRegistry()
        registry.ingest_execution_trace(["A", "B"], ["code"])
        registry.ingest_execution_trace(["C", "D"], ["code"])
        result = registry.get_hyperedge_patterns()
        assert len(result) == 2

    def test_high_min_weight_filters_all(self) -> None:
        """min_weight above all occurrence counts returns empty list."""
        registry = MyceliumRegistry()
        registry.ingest_execution_trace(["A"], ["code"])  # weight=1.0
        result = registry.get_hyperedge_patterns(min_weight=999.0)
        assert result == []

    def test_returns_snapshot_not_live_list(self) -> None:
        """Result is a fresh list — mutating it does not affect the registry."""
        registry = MyceliumRegistry()
        registry.ingest_execution_trace(["X"], ["domain"])
        snapshot = registry.get_hyperedge_patterns()
        snapshot.clear()
        assert len(registry.hyperedges) == 1
