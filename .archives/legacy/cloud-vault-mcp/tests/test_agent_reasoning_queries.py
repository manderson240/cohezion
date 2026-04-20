"""Unit tests for Phase 2 agent reasoning queries.

Tests the 4 key query patterns:
- root_cause_analysis: Find reasoning chains for decisions
- contradiction_detection: Find lessons that contradict decisions
- cascade_impact: Trace decision impacts on downstream decisions
- high_confidence_reasoning: Find well-justified decisions for reuse
"""

from unittest.mock import MagicMock

import pytest

from src.mcp_server.agent_reasoning_queries import AgentReasoningQueries


class MockSurrealDBSync:
    """Mock SurrealDB sync for testing."""

    def __init__(self):
        self.queries = []
        self.response_map = {}

    def _execute_query(self, query: str):
        """Mock query execution."""
        self.queries.append(query)

        # Check if we have a prepared response
        for pattern, response in self.response_map.items():
            if pattern in query:
                return response

        # Default empty response
        return []

    def set_response(self, pattern: str, response):
        """Set a canned response for a query pattern."""
        self.response_map[pattern] = response


@pytest.fixture
def mock_db():
    """Provide a mock SurrealDB instance."""
    return MockSurrealDBSync()


@pytest.fixture
def reasoning_queries(mock_db):
    """Provide an AgentReasoningQueries instance with mock DB."""
    return AgentReasoningQueries(mock_db)


class TestRootCauseAnalysis:
    """Tests for root_cause_analysis query."""

    def test_root_cause_single_reasoning(self, mock_db, reasoning_queries):
        """Test root cause analysis with single reasoning chain."""
        mock_db.set_response(
            "SELECT * FROM agent_reasoning",
            [
                {
                    "id": "agent_reasoning:test123",
                    "decision_id": "agent_decision:test",
                    "reasoning_type": "research",
                    "confidence_score": 0.92,
                    "reasoning_chain": [
                        "Step 1: Review",
                        "Step 2: Analyze",
                        "Step 3: Decide",
                    ],
                    "assumptions": ["Assumption 1"],
                    "alternatives_rejected": [{"option": "Alt", "reason": "Rejected"}],
                    "created_at": "2026-02-12T10:00:00Z",
                }
            ],
        )

        result = reasoning_queries.root_cause_analysis("agent_decision:test")

        assert result["success"] is True
        assert result["decision_id"] == "agent_decision:test"
        assert result["total_chains"] == 1
        assert result["highest_confidence"] == 0.92
        assert len(result["reasoning_chains"]) == 1

        chain = result["reasoning_chains"][0]
        assert chain["reasoning_type"] == "research"
        assert chain["confidence_score"] == 0.92
        assert chain["chain_length"] == 3

    def test_root_cause_multiple_reasoning(self, mock_db, reasoning_queries):
        """Test root cause analysis with multiple reasoning chains."""
        mock_db.set_response(
            "SELECT * FROM agent_reasoning",
            [
                {
                    "id": "agent_reasoning:1",
                    "decision_id": "agent_decision:test",
                    "reasoning_type": "research",
                    "confidence_score": 0.95,
                    "reasoning_chain": ["Step 1"],
                    "assumptions": [],
                    "alternatives_rejected": [],
                    "created_at": "2026-02-12T10:00:00Z",
                },
                {
                    "id": "agent_reasoning:2",
                    "decision_id": "agent_decision:test",
                    "reasoning_type": "pattern",
                    "confidence_score": 0.78,
                    "reasoning_chain": ["Step 1", "Step 2"],
                    "assumptions": ["Assumption"],
                    "alternatives_rejected": [],
                    "created_at": "2026-02-12T11:00:00Z",
                },
            ],
        )

        result = reasoning_queries.root_cause_analysis("agent_decision:test")

        assert result["success"] is True
        assert result["total_chains"] == 2
        assert result["highest_confidence"] == 0.95
        # Verify ordered by confidence (highest first)
        assert result["reasoning_chains"][0]["confidence_score"] == 0.95
        assert result["reasoning_chains"][1]["confidence_score"] == 0.78

    def test_root_cause_not_found(self, mock_db, reasoning_queries):
        """Test root cause analysis when decision not found."""
        mock_db.set_response("SELECT * FROM agent_reasoning", [])

        result = reasoning_queries.root_cause_analysis("agent_decision:nonexistent")

        assert result["success"] is False
        assert "Decision not found" in result["error"]

    def test_root_cause_exception(self, mock_db, reasoning_queries):
        """Test root cause analysis with database error."""
        mock_db._execute_query = MagicMock(side_effect=Exception("DB error"))

        result = reasoning_queries.root_cause_analysis("agent_decision:test")

        assert result["success"] is False
        assert "DB error" in result["error"]


class TestContradictionDetection:
    """Tests for contradiction_detection query."""

    def test_contradiction_all_severities(self, mock_db, reasoning_queries):
        """Test contradiction detection without severity filter."""
        mock_db.set_response(
            "SELECT",
            [
                {
                    "decision_id": "agent_decision:1",
                    "lesson_id": "lesson-01",
                    "challenge_type": "contradicts",
                    "severity": "major",
                    "notes": "Major contradiction",
                    "created_at": "2026-02-12T10:00:00Z",
                },
                {
                    "decision_id": "agent_decision:2",
                    "lesson_id": "lesson-02",
                    "challenge_type": "limits",
                    "severity": "minor",
                    "notes": "Minor limitation",
                    "created_at": "2026-02-12T11:00:00Z",
                },
            ],
        )

        result = reasoning_queries.contradiction_detection()

        assert result["success"] is True
        assert result["total_count"] == 2
        assert result["major_count"] == 1
        assert len(result["contradictions"]) == 2

    def test_contradiction_filter_major(self, mock_db, reasoning_queries):
        """Test contradiction detection filtered by major severity."""
        mock_db.set_response(
            "WHERE severity = 'major'",
            [
                {
                    "decision_id": "agent_decision:1",
                    "lesson_id": "lesson-01",
                    "challenge_type": "contradicts",
                    "severity": "major",
                    "notes": "Major contradiction",
                    "created_at": "2026-02-12T10:00:00Z",
                },
            ],
        )

        result = reasoning_queries.contradiction_detection(severity_filter="major")

        assert result["success"] is True
        assert result["total_count"] == 1
        assert result["severity_filter"] == "major"
        assert result["contradictions"][0]["severity"] == "major"

    def test_contradiction_filter_minor(self, mock_db, reasoning_queries):
        """Test contradiction detection filtered by minor severity."""
        mock_db.set_response(
            "WHERE severity = 'minor'",
            [
                {
                    "decision_id": "agent_decision:2",
                    "lesson_id": "lesson-02",
                    "challenge_type": "limits",
                    "severity": "minor",
                    "notes": "Minor limitation",
                    "created_at": "2026-02-12T11:00:00Z",
                },
            ],
        )

        result = reasoning_queries.contradiction_detection(severity_filter="minor")

        assert result["success"] is True
        assert result["total_count"] == 1
        assert result["contradictions"][0]["severity"] == "minor"

    def test_contradiction_invalid_severity(self, reasoning_queries):
        """Test contradiction detection with invalid severity filter."""
        result = reasoning_queries.contradiction_detection(severity_filter="invalid")

        assert result["success"] is False
        assert "Invalid severity" in result["error"]

    def test_contradiction_empty(self, mock_db, reasoning_queries):
        """Test contradiction detection with no results."""
        mock_db.set_response("SELECT", [])

        result = reasoning_queries.contradiction_detection()

        assert result["success"] is True
        assert result["total_count"] == 0
        assert len(result["contradictions"]) == 0


class TestCascadeImpact:
    """Tests for cascade_impact query."""

    def test_cascade_single_impact(self, mock_db, reasoning_queries):
        """Test cascade impact with single dependent decision."""
        mock_db.set_response(
            "FROM relates_to_decision",
            [
                {
                    "source_decision": "agent_decision:source",
                    "dependent_decision": "agent_decision:dep1",
                    "dependency_type": "blocks",
                    "impact_level": "critical",
                    "notes": "Must resolve first",
                    "created_at": "2026-02-12T10:00:00Z",
                },
            ],
        )

        result = reasoning_queries.cascade_impact("agent_decision:source")

        assert result["success"] is True
        assert result["source_decision"] == "agent_decision:source"
        assert result["total_cascades"] == 1
        assert result["critical_count"] == 1
        assert result["significant_count"] == 0
        assert result["minor_count"] == 0

    def test_cascade_multiple_impacts(self, mock_db, reasoning_queries):
        """Test cascade impact with multiple dependent decisions."""
        mock_db.set_response(
            "FROM relates_to_decision",
            [
                {
                    "source_decision": "agent_decision:source",
                    "dependent_decision": "agent_decision:dep1",
                    "dependency_type": "blocks",
                    "impact_level": "critical",
                    "notes": "Blocks execution",
                    "created_at": "2026-02-12T10:00:00Z",
                },
                {
                    "source_decision": "agent_decision:source",
                    "dependent_decision": "agent_decision:dep2",
                    "dependency_type": "enables",
                    "impact_level": "significant",
                    "notes": "Enables new feature",
                    "created_at": "2026-02-12T11:00:00Z",
                },
                {
                    "source_decision": "agent_decision:source",
                    "dependent_decision": "agent_decision:dep3",
                    "dependency_type": "refines",
                    "impact_level": "minor",
                    "notes": "Refines approach",
                    "created_at": "2026-02-12T12:00:00Z",
                },
            ],
        )

        result = reasoning_queries.cascade_impact("agent_decision:source")

        assert result["success"] is True
        assert result["total_cascades"] == 3
        assert result["critical_count"] == 1
        assert result["significant_count"] == 1
        assert result["minor_count"] == 1

    def test_cascade_no_impact(self, mock_db, reasoning_queries):
        """Test cascade impact with no cascades."""
        mock_db.set_response("FROM relates_to_decision", [])

        result = reasoning_queries.cascade_impact("agent_decision:isolated")

        assert result["success"] is True
        assert result["total_cascades"] == 0
        assert result["critical_count"] == 0


class TestHighConfidenceReasoning:
    """Tests for high_confidence_reasoning query."""

    def test_high_confidence_single_result(self, mock_db, reasoning_queries):
        """Test high confidence reasoning with single result."""
        mock_db.set_response(
            "WHERE confidence_score",
            [
                {
                    "id": "agent_reasoning:high1",
                    "decision_id": "agent_decision:1",
                    "reasoning_type": "research",
                    "confidence_score": 0.95,
                    "reasoning_chain": ["Step 1", "Step 2", "Step 3"],
                    "assumptions": ["Assumption 1", "Assumption 2"],
                    "created_at": "2026-02-12T10:00:00Z",
                },
            ],
        )

        result = reasoning_queries.high_confidence_reasoning(confidence_threshold=0.9)

        assert result["success"] is True
        assert result["total_count"] == 1
        assert result["confidence_threshold"] == 0.9
        assert result["avg_confidence"] == 0.95
        assert result["reasoning_types"]["research"] == 1

    def test_high_confidence_multiple_types(self, mock_db, reasoning_queries):
        """Test high confidence reasoning with multiple reasoning types."""
        mock_db.set_response(
            "WHERE confidence_score",
            [
                {
                    "id": "agent_reasoning:1",
                    "decision_id": "agent_decision:1",
                    "reasoning_type": "research",
                    "confidence_score": 0.95,
                    "reasoning_chain": ["Step 1"],
                    "assumptions": [],
                    "created_at": "2026-02-12T10:00:00Z",
                },
                {
                    "id": "agent_reasoning:2",
                    "decision_id": "agent_decision:2",
                    "reasoning_type": "pattern",
                    "confidence_score": 0.88,
                    "reasoning_chain": ["Step 1", "Step 2"],
                    "assumptions": ["Assumption"],
                    "created_at": "2026-02-12T11:00:00Z",
                },
                {
                    "id": "agent_reasoning:3",
                    "decision_id": "agent_decision:3",
                    "reasoning_type": "hybrid",
                    "confidence_score": 0.82,
                    "reasoning_chain": ["Step 1", "Step 2", "Step 3"],
                    "assumptions": ["A1", "A2"],
                    "created_at": "2026-02-12T12:00:00Z",
                },
            ],
        )

        result = reasoning_queries.high_confidence_reasoning(confidence_threshold=0.80)

        assert result["success"] is True
        assert result["total_count"] == 3
        assert result["avg_confidence"] == pytest.approx(0.883, abs=0.01)
        assert result["min_confidence"] == 0.82
        assert result["max_confidence"] == 0.95
        assert result["reasoning_types"]["research"] == 1
        assert result["reasoning_types"]["pattern"] == 1
        assert result["reasoning_types"]["hybrid"] == 1

    def test_high_confidence_threshold_validation(self, reasoning_queries):
        """Test high confidence reasoning with invalid threshold."""
        result = reasoning_queries.high_confidence_reasoning(confidence_threshold=1.5)

        assert result["success"] is False
        assert "confidence_threshold must be between 0.0 and 1.0" in result["error"]

    def test_high_confidence_empty(self, mock_db, reasoning_queries):
        """Test high confidence reasoning with no results."""
        mock_db.set_response("WHERE confidence_score", [])

        result = reasoning_queries.high_confidence_reasoning(confidence_threshold=0.99)

        assert result["success"] is True
        assert result["total_count"] == 0
        assert result["avg_confidence"] == 0.0


class TestReasoningByType:
    """Tests for reasoning_by_type helper query."""

    def test_reasoning_by_type_research(self, mock_db, reasoning_queries):
        """Test filtering reasoning by research type."""
        mock_db.set_response(
            "WHERE reasoning_type = 'research'",
            [
                {
                    "id": "agent_reasoning:1",
                    "decision_id": "agent_decision:1",
                    "reasoning_type": "research",
                    "confidence_score": 0.92,
                    "created_at": "2026-02-12T10:00:00Z",
                },
                {
                    "id": "agent_reasoning:2",
                    "decision_id": "agent_decision:2",
                    "reasoning_type": "research",
                    "confidence_score": 0.88,
                    "created_at": "2026-02-12T11:00:00Z",
                },
            ],
        )

        result = reasoning_queries.reasoning_by_type("research")

        assert result["success"] is True
        assert result["total_count"] == 2
        assert result["reasoning_type"] == "research"
        assert result["avg_confidence"] == 0.9

    def test_reasoning_by_type_all_types(self, mock_db, reasoning_queries):
        """Test all valid reasoning types."""
        mock_db.set_response("WHERE reasoning_type", [{"id": "test"}])

        types = ["research", "pattern", "intuition", "convention", "hybrid"]

        for reasoning_type in types:
            result = reasoning_queries.reasoning_by_type(reasoning_type)
            assert result["success"] is True
            assert result["reasoning_type"] == reasoning_type

    def test_reasoning_by_type_invalid(self, reasoning_queries):
        """Test with invalid reasoning type."""
        result = reasoning_queries.reasoning_by_type("invalid_type")

        assert result["success"] is False
        assert "Invalid reasoning_type" in result["error"]


class TestQueryErrorHandling:
    """Tests for error handling across all queries."""

    def test_root_cause_exception(self, mock_db, reasoning_queries):
        """Test exception handling in root_cause_analysis."""
        mock_db._execute_query = MagicMock(side_effect=Exception("DB error"))

        result = reasoning_queries.root_cause_analysis("test")

        assert result["success"] is False
        assert "DB error" in result["error"]

    def test_contradiction_exception(self, mock_db, reasoning_queries):
        """Test exception handling in contradiction_detection."""
        mock_db._execute_query = MagicMock(side_effect=Exception("DB error"))

        result = reasoning_queries.contradiction_detection()

        assert result["success"] is False
        assert "DB error" in result["error"]

    def test_cascade_exception(self, mock_db, reasoning_queries):
        """Test exception handling in cascade_impact."""
        mock_db._execute_query = MagicMock(side_effect=Exception("DB error"))

        result = reasoning_queries.cascade_impact("test")

        assert result["success"] is False
        assert "DB error" in result["error"]

    def test_high_confidence_exception(self, mock_db, reasoning_queries):
        """Test exception handling in high_confidence_reasoning."""
        mock_db._execute_query = MagicMock(side_effect=Exception("DB error"))

        result = reasoning_queries.high_confidence_reasoning()

        assert result["success"] is False
        assert "DB error" in result["error"]


class TestQueryStructure:
    """Tests for proper SurrealDB query structure."""

    def test_root_cause_query_syntax(self, mock_db, reasoning_queries):
        """Verify root_cause_analysis generates valid queries."""
        mock_db.set_response("SELECT * FROM", [{"id": "test"}])

        reasoning_queries.root_cause_analysis("test_decision")

        # Verify SELECT query was executed
        select_queries = [
            q for q in mock_db.queries if "SELECT * FROM agent_reasoning" in q
        ]
        assert len(select_queries) > 0
        assert "decision_id" in select_queries[0]
        assert "ORDER BY" in select_queries[0]

    def test_contradiction_query_syntax(self, mock_db, reasoning_queries):
        """Verify contradiction_detection generates valid queries."""
        mock_db.set_response("SELECT", [])

        reasoning_queries.contradiction_detection()

        # Verify SELECT query was executed
        select_queries = [q for q in mock_db.queries if "FROM challenges_lesson" in q]
        assert len(select_queries) > 0
        assert "ORDER BY" in select_queries[0]

    def test_cascade_query_syntax(self, mock_db, reasoning_queries):
        """Verify cascade_impact generates valid queries."""
        mock_db.set_response("FROM relates_to_decision", [])

        reasoning_queries.cascade_impact("test_decision")

        # Verify SELECT query was executed
        select_queries = [q for q in mock_db.queries if "FROM relates_to_decision" in q]
        assert len(select_queries) > 0
        assert "test_decision" in select_queries[0]

    def test_high_confidence_query_syntax(self, mock_db, reasoning_queries):
        """Verify high_confidence_reasoning generates valid queries."""
        mock_db.set_response("WHERE confidence_score", [])

        reasoning_queries.high_confidence_reasoning(confidence_threshold=0.8)

        # Verify SELECT query was executed
        select_queries = [q for q in mock_db.queries if "confidence_score >= 0.8" in q]
        assert len(select_queries) > 0
