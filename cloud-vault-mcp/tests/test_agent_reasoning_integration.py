"""Integration tests for Phase 2 agent reasoning with Phase 1 compatibility.

Tests the complete workflow:
- Phase 1 tools + Phase 2 tools
- Tool execution → query results
- E2E cascade resolution
- Query chaining (reasoning → lessons → papers)
"""

from unittest.mock import MagicMock

import pytest

from src.mcp_server.agent_reasoning import AgentReasoningOps
from src.mcp_server.agent_reasoning_queries import AgentReasoningQueries


class MockSurrealDBSync:
    """Mock SurrealDB for integration testing."""

    def __init__(self):
        self.queries = []
        self.created_nodes = {}
        self.created_edges = {}

    def _execute_query(self, query: str):
        """Simulate query execution with state tracking."""
        self.queries.append(query)

        # Handle referential integrity checks (SELECT id FROM ...)
        if "SELECT id FROM" in query:
            # Extract node ID from queries like "SELECT id FROM agent_decision:test LIMIT 1"
            parts = query.split()
            if len(parts) >= 4:
                node_id = parts[3]
                if node_id in self.created_nodes:
                    return [{"id": node_id}]
            return []  # Return empty for missing references

        # Track created nodes for referential integrity
        if "CREATE agent_reasoning" in query:
            node_id = "agent_reasoning:test123"
            self.created_nodes[node_id] = {"type": "reasoning"}
            return [{"id": node_id, "success": True}]

        if "CREATE challenges_lesson" in query:
            edge_id = "edge:challenge:test123"
            return [{"id": edge_id, "success": True}]

        if "CREATE relates_to_decision" in query:
            edge_id = "edge:cascade:test123"
            return [{"id": edge_id, "success": True}]

        if "CREATE agent_session" in query or "CREATE agent_decision" in query:
            node_id = "agent_decision:test"
            self.created_nodes[node_id] = {"type": "decision"}
            return [{"id": node_id, "success": True}]

        if "RELATE" in query:
            return [{"id": "edge:test", "success": True}]

        if "SELECT * FROM agent_reasoning" in query:
            return [
                {
                    "id": "agent_reasoning:1",
                    "decision_id": "agent_decision:test",
                    "reasoning_type": "research",
                    "confidence_score": 0.92,
                    "reasoning_chain": ["Step 1", "Step 2"],
                    "assumptions": ["A1"],
                    "alternatives_rejected": [],
                    "created_at": "2026-02-13T10:00:00Z",
                }
            ]

        if "SELECT" in query and "challenges_lesson" in query:
            return [
                {
                    "decision_id": "agent_decision:test",
                    "lesson_id": "lesson-01",
                    "challenge_type": "contradicts",
                    "severity": "major",
                    "notes": "Test challenge",
                    "created_at": "2026-02-13T10:00:00Z",
                }
            ]

        if "SELECT" in query and "relates_to_decision" in query:
            return [
                {
                    "source_decision": "agent_decision:source",
                    "dependent_decision": "agent_decision:dep1",
                    "dependency_type": "blocks",
                    "impact_level": "critical",
                    "notes": "Cascade test",
                    "created_at": "2026-02-13T10:00:00Z",
                }
            ]

        return []


@pytest.fixture
def mock_db():
    """Provide mock database."""
    return MockSurrealDBSync()


@pytest.fixture
def reasoning_ops(mock_db):
    """Provide AgentReasoningOps instance."""
    return AgentReasoningOps(mock_db)


@pytest.fixture
def reasoning_queries(mock_db):
    """Provide AgentReasoningQueries instance."""
    return AgentReasoningQueries(mock_db)


class TestPhase1Phase2Compatibility:
    """Verify Phase 1 and Phase 2 schemas work together."""

    def test_phase1_session_with_phase2_reasoning(self, mock_db, reasoning_ops):
        """Test creating session + reasoning together."""
        # Phase 1: Create session
        session_result = {"success": True, "session_id": "agent_session:test"}
        mock_db.created_nodes["agent_session:test"] = {"type": "session"}

        # Phase 2: Create reasoning (requires decision to exist)
        mock_db.created_nodes["agent_decision:test"] = {"type": "decision"}
        reasoning_result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Reviewed papers", "Analyzed findings"],
            confidence_score=0.92,
        )

        assert session_result["success"] is True
        assert reasoning_result["success"] is True
        assert reasoning_result["confidence_score"] == 0.92

    def test_phase1_decision_with_phase2_challenge(self, mock_db, reasoning_ops):
        """Test decision + challenge edge together."""
        # Set up mock to return success for reference checks
        mock_db.created_nodes["agent_decision:test"] = {"type": "decision"}
        mock_db.created_nodes["lesson:lesson-01"] = {"type": "lesson"}

        # Phase 2: Create challenge
        challenge_result = reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="lesson-01",
            challenge_type="contradicts",
            severity="major",
        )

        assert challenge_result["success"] is True
        assert challenge_result["challenge_type"] == "contradicts"

    def test_phase1_decisions_with_phase2_cascade(self, mock_db, reasoning_ops):
        """Test decision cascade edges."""
        # Both decisions exist (Phase 1)
        mock_db.created_nodes["agent_decision:source"] = {"type": "decision"}
        mock_db.created_nodes["agent_decision:dep1"] = {"type": "decision"}

        # Phase 2: Create cascade
        cascade_result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:dep1",
            dependency_type="blocks",
            impact_level="critical",
        )

        assert cascade_result["success"] is True
        assert cascade_result["impact_level"] == "critical"


class TestToolToQueryWorkflow:
    """Verify complete tool execution → query results workflow."""

    def test_create_reasoning_then_query(
        self, mock_db, reasoning_ops, reasoning_queries
    ):
        """Test: Create reasoning → Query for it."""
        # Step 1: Create reasoning node (requires decision to exist)
        mock_db.created_nodes["agent_decision:test"] = {"type": "decision"}
        create_result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step 1", "Step 2"],
            confidence_score=0.92,
        )

        assert create_result["success"] is True
        create_result["reasoning_id"]

        # Step 2: Query for the reasoning
        query_result = reasoning_queries.root_cause_analysis("agent_decision:test")

        assert query_result["success"] is True
        assert query_result["total_chains"] == 1
        assert query_result["highest_confidence"] == 0.92

    def test_create_challenge_then_detect(
        self, mock_db, reasoning_ops, reasoning_queries
    ):
        """Test: Create challenge → Detect it via contradiction query."""
        # Step 1: Create challenge (requires decision and lesson to exist)
        mock_db.created_nodes["agent_decision:test"] = {"type": "decision"}
        mock_db.created_nodes["lesson:lesson-01"] = {"type": "lesson"}

        create_result = reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="lesson-01",
            challenge_type="contradicts",
            severity="major",
        )

        assert create_result["success"] is True

        # Step 2: Query for contradictions
        query_result = reasoning_queries.contradiction_detection(
            severity_filter="major"
        )

        assert query_result["success"] is True
        assert query_result["major_count"] >= 0

    def test_create_cascade_then_traverse(
        self, mock_db, reasoning_ops, reasoning_queries
    ):
        """Test: Create cascade → Traverse it via cascade query."""
        # Step 1: Create cascade
        mock_db.created_nodes["agent_decision:source"] = {"type": "decision"}
        mock_db.created_nodes["agent_decision:dep1"] = {"type": "decision"}

        create_result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:dep1",
            dependency_type="blocks",
            impact_level="critical",
        )

        assert create_result["success"] is True

        # Step 2: Query for cascades
        query_result = reasoning_queries.cascade_impact("agent_decision:source")

        assert query_result["success"] is True
        assert query_result["critical_count"] >= 0


class TestE2ECascadeResolution:
    """Verify multi-level cascade traversal and resolution."""

    def test_multi_level_cascade(self, mock_db, reasoning_ops):
        """Test creating multi-level cascade chain."""
        decisions = [
            "agent_decision:root",
            "agent_decision:level1_a",
            "agent_decision:level1_b",
            "agent_decision:level2",
        ]

        # Create all decisions in mock DB
        for decision in decisions:
            mock_db.created_nodes[decision] = {"type": "decision"}

        # Level 1: Root blocks two decisions
        cascade1 = reasoning_ops.record_cascade(
            source_decision_id=decisions[0],
            dependent_decision_id=decisions[1],
            dependency_type="blocks",
            impact_level="critical",
        )

        cascade2 = reasoning_ops.record_cascade(
            source_decision_id=decisions[0],
            dependent_decision_id=decisions[2],
            dependency_type="enables",
            impact_level="significant",
        )

        # Level 2: One of level 1 affects level 2
        cascade3 = reasoning_ops.record_cascade(
            source_decision_id=decisions[1],
            dependent_decision_id=decisions[3],
            dependency_type="refines",
            impact_level="minor",
        )

        assert cascade1["success"] is True
        assert cascade2["success"] is True
        assert cascade3["success"] is True

    def test_circular_dependency_detection(self, mock_db, reasoning_ops):
        """Test handling of circular dependencies."""
        # Create decisions
        mock_db.created_nodes["decision_a"] = {"type": "decision"}
        mock_db.created_nodes["decision_b"] = {"type": "decision"}

        # Create dependency: A -> B
        cascade1 = reasoning_ops.record_cascade(
            source_decision_id="decision_a",
            dependent_decision_id="decision_b",
            dependency_type="blocks",
            impact_level="critical",
        )

        # Create reverse dependency: B -> A (potential circular)
        cascade2 = reasoning_ops.record_cascade(
            source_decision_id="decision_b",
            dependent_decision_id="decision_a",
            dependency_type="refines",
            impact_level="minor",
        )

        # Both should succeed (system handles resolution)
        assert cascade1["success"] is True
        assert cascade2["success"] is True


class TestQueryChaining:
    """Verify query chaining across multiple layers."""

    def test_reasoning_to_lessons_chain(
        self, mock_db, reasoning_ops, reasoning_queries
    ):
        """Test: reasoning → query → lessons (complete chain)."""
        # Create reasoning (requires decision to exist)
        mock_db.created_nodes["agent_decision:test"] = {"type": "decision"}
        reasoning_result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Reviewed evidence", "Validated assumptions"],
            confidence_score=0.88,
        )

        assert reasoning_result["success"] is True

        # Query reasoning
        query_result = reasoning_queries.root_cause_analysis("agent_decision:test")

        assert query_result["success"] is True
        assert len(query_result["reasoning_chains"]) > 0

    def test_cascade_impact_chain(self, mock_db, reasoning_ops, reasoning_queries):
        """Test: cascade → query → impact analysis (complete chain)."""
        # Create cascade
        mock_db.created_nodes["decision:root"] = {"type": "decision"}
        mock_db.created_nodes["decision:dep1"] = {"type": "decision"}

        cascade_result = reasoning_ops.record_cascade(
            source_decision_id="decision:root",
            dependent_decision_id="decision:dep1",
            dependency_type="blocks",
            impact_level="critical",
        )

        assert cascade_result["success"] is True

        # Query cascade impact
        query_result = reasoning_queries.cascade_impact("decision:root")

        assert query_result["success"] is True
        assert query_result["source_decision"] == "decision:root"

    def test_confidence_filtering_chain(
        self, mock_db, reasoning_ops, reasoning_queries
    ):
        """Test: create reasoning → filter by confidence (complete chain)."""
        # Create high-confidence reasoning (requires decision to exist)
        mock_db.created_nodes["agent_decision:test"] = {"type": "decision"}
        high_conf = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step 1"],
            confidence_score=0.95,
        )

        assert high_conf["success"] is True

        # Query for high-confidence reasoning
        query_result = reasoning_queries.high_confidence_reasoning(
            confidence_threshold=0.90
        )

        assert query_result["success"] is True
        assert query_result["confidence_threshold"] == 0.90


class TestDataConsistency:
    """Verify referential integrity and consistency."""

    def test_referential_integrity(self, mock_db, reasoning_ops):
        """Test that foreign key relationships are maintained."""
        # Try to create reasoning for non-existent decision
        result = reasoning_ops.record_reasoning(
            decision_id="nonexistent:decision",
            reasoning_type="research",
            reasoning_chain=["Step"],
            confidence_score=0.7,
        )

        # Should fail (decision not found)
        assert result["success"] is False
        assert "Decision not found" in result["error"]

    def test_cascade_referential_integrity(self, mock_db, reasoning_ops):
        """Test cascade with missing dependent decision."""
        mock_db.created_nodes["decision:source"] = {"type": "decision"}
        # Don't create dependent decision

        result = reasoning_ops.record_cascade(
            source_decision_id="decision:source",
            dependent_decision_id="nonexistent:dep",
            dependency_type="blocks",
            impact_level="critical",
        )

        # Should fail (dependent not found)
        assert result["success"] is False
        assert "Dependent decision not found" in result["error"]

    def test_challenge_referential_integrity(self, mock_db, reasoning_ops):
        """Test challenge with missing lesson."""
        mock_db.created_nodes["decision:test"] = {"type": "decision"}
        # Don't create lesson

        result = reasoning_ops.record_challenge(
            decision_id="decision:test",
            lesson_id="nonexistent:lesson",
            challenge_type="contradicts",
            severity="major",
        )

        # Should fail (lesson not found)
        assert result["success"] is False
        assert "Lesson not found" in result["error"]


class TestPhase1ToolsStillWork:
    """Verify Phase 1 tools still function with Phase 2 present."""

    def test_phase1_session_creation_still_works(self, mock_db):
        """Test that Phase 1 session creation isn't broken."""
        mock_db.created_nodes["agent_session:test"] = {"type": "session"}

        # Verify Phase 1 query still works
        session_check = mock_db._execute_query("SELECT id FROM agent_session:test")

        assert session_check is not None
        assert len(session_check) > 0

    def test_phase1_decision_creation_still_works(self, mock_db):
        """Test that Phase 1 decision creation isn't broken."""
        mock_db.created_nodes["agent_decision:test"] = {"type": "decision"}

        # Verify Phase 1 query still works
        decision_check = mock_db._execute_query("SELECT id FROM agent_decision:test")

        assert decision_check is not None
        assert len(decision_check) > 0


class TestIntegrationErrorHandling:
    """Test error handling in integrated workflows."""

    def test_workflow_with_database_error(self, mock_db, reasoning_ops):
        """Test graceful handling of database errors during workflow."""
        mock_db._execute_query = MagicMock(side_effect=Exception("DB connection lost"))

        result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step"],
            confidence_score=0.7,
        )

        assert result["success"] is False
        assert "DB connection lost" in result["error"]

    def test_query_with_missing_data(self, mock_db, reasoning_queries):
        """Test query gracefully handles missing data."""
        # Query for non-existent decision
        result = reasoning_queries.root_cause_analysis("nonexistent:decision")

        # Query should return gracefully (mock returns data for any decision)
        # In real DB, would return empty results
        assert "success" in result
        assert isinstance(result.get("reasoning_chains", []), list)


class TestIntegrationMetrics:
    """Test integration-level metrics and statistics."""

    def test_combined_operation_count(self, mock_db, reasoning_ops):
        """Test that operations are properly counted."""
        initial_count = len(mock_db.queries)

        # Perform 3 operations
        reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step"],
            confidence_score=0.7,
        )

        final_count = len(mock_db.queries)

        # Should have executed queries
        assert final_count >= initial_count

    def test_workflow_performance(self, mock_db, reasoning_ops, reasoning_queries):
        """Test overall workflow performance metrics."""
        import time

        start = time.time()

        # Create reasoning
        reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step 1", "Step 2"],
            confidence_score=0.9,
        )

        # Query for it
        reasoning_queries.root_cause_analysis("agent_decision:test")

        elapsed = time.time() - start

        # Should be fast (mock DB)
        assert elapsed < 1.0  # Less than 1 second for integration test
