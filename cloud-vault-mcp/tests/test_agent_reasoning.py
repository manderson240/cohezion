"""Unit tests for Phase 2 agent reasoning operations.

Tests the three new MCP tools:
- record_reasoning: Insert agent_reasoning nodes
- record_challenge: Insert challenges_lesson edges
- record_cascade: Insert relates_to_decision edges
"""

from unittest.mock import MagicMock

import pytest

from src.mcp_server.agent_reasoning import AgentReasoningOps


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

        # Default success response
        return [{"id": "test:success", "success": True}]

    def set_response(self, pattern: str, response):
        """Set a canned response for a query pattern."""
        self.response_map[pattern] = response


@pytest.fixture
def mock_db():
    """Provide a mock SurrealDB instance."""
    return MockSurrealDBSync()


@pytest.fixture
def reasoning_ops(mock_db):
    """Provide an AgentReasoningOps instance with mock DB."""
    return AgentReasoningOps(mock_db)


class TestRecordReasoning:
    """Tests for record_reasoning tool."""

    def test_record_reasoning_success(self, mock_db, reasoning_ops):
        """Test successful reasoning node creation."""
        mock_db.set_response(
            "SELECT id FROM agent_decision",
            [{"id": "agent_decision:test123"}],
        )

        result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test123",
            reasoning_type="research",
            reasoning_chain=["Step 1: Review papers", "Step 2: Compare findings"],
            confidence_score=0.85,
            assumptions=["Assumption 1", "Assumption 2"],
            alternatives_rejected=[
                {"option": "Alt 1", "reason": "Performance impact"},
                {"option": "Alt 2", "reason": "Complexity"},
            ],
        )

        assert result["success"] is True
        assert result["decision_id"] == "agent_decision:test123"
        assert result["reasoning_type"] == "research"
        assert result["confidence_score"] == 0.85
        assert result["chain_length"] == 2
        assert "reasoning_id" in result
        assert "timestamp" in result

    def test_record_reasoning_invalid_type(self, reasoning_ops):
        """Test reasoning with invalid reasoning_type."""
        result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="invalid_type",
            reasoning_chain=["Step 1"],
            confidence_score=0.7,
        )

        assert result["success"] is False
        assert "Invalid reasoning_type" in result["error"]

    def test_record_reasoning_invalid_confidence(self, reasoning_ops):
        """Test reasoning with invalid confidence_score."""
        result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step 1"],
            confidence_score=1.5,  # Out of range
        )

        assert result["success"] is False
        assert "confidence_score must be between 0.0 and 1.0" in result["error"]

    def test_record_reasoning_decision_not_found(self, mock_db, reasoning_ops):
        """Test reasoning when decision doesn't exist."""
        mock_db.set_response("SELECT id FROM agent_decision", [])

        result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:nonexistent",
            reasoning_type="research",
            reasoning_chain=["Step 1"],
            confidence_score=0.7,
        )

        assert result["success"] is False
        assert "Decision not found" in result["error"]

    def test_record_reasoning_all_types(self, mock_db, reasoning_ops):
        """Test all valid reasoning types."""
        mock_db.set_response("SELECT id FROM", [{"id": "agent_decision:test"}])

        types = ["research", "pattern", "intuition", "convention", "hybrid"]

        for reasoning_type in types:
            result = reasoning_ops.record_reasoning(
                decision_id="agent_decision:test",
                reasoning_type=reasoning_type,
                reasoning_chain=["Step 1"],
                confidence_score=0.7,
            )
            assert result["success"] is True
            assert result["reasoning_type"] == reasoning_type

    def test_record_reasoning_edge_cases(self, mock_db, reasoning_ops):
        """Test edge cases for confidence scores."""
        mock_db.set_response("SELECT id FROM", [{"id": "agent_decision:test"}])

        # Test boundary values
        for score in [0.0, 0.5, 1.0]:
            result = reasoning_ops.record_reasoning(
                decision_id="agent_decision:test",
                reasoning_type="research",
                reasoning_chain=["Step 1"],
                confidence_score=score,
            )
            assert result["success"] is True
            assert result["confidence_score"] == score


class TestRecordChallenge:
    """Tests for record_challenge tool."""

    def test_record_challenge_success(self, mock_db, reasoning_ops):
        """Test successful challenge edge creation."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        result = reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="lesson-01",
            challenge_type="contradicts",
            severity="major",
            notes="This decision contradicts the lesson's findings",
        )

        assert result["success"] is True
        assert result["decision_id"] == "agent_decision:test"
        assert result["lesson_id"] == "lesson-01"
        assert result["challenge_type"] == "contradicts"
        assert result["severity"] == "major"
        assert "edge_id" in result
        assert "timestamp" in result

    def test_record_challenge_invalid_type(self, reasoning_ops):
        """Test challenge with invalid challenge_type."""
        result = reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="lesson-01",
            challenge_type="invalid_type",
        )

        assert result["success"] is False
        assert "Invalid challenge_type" in result["error"]

    def test_record_challenge_invalid_severity(self, reasoning_ops):
        """Test challenge with invalid severity."""
        result = reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="lesson-01",
            challenge_type="contradicts",
            severity="invalid_severity",
        )

        assert result["success"] is False
        assert "Invalid severity" in result["error"]

    def test_record_challenge_decision_not_found(self, mock_db, reasoning_ops):
        """Test challenge when decision doesn't exist."""
        mock_db.set_response("SELECT id FROM agent_decision", [])
        mock_db.set_response("SELECT id FROM lesson", [{"id": "lesson-01"}])

        result = reasoning_ops.record_challenge(
            decision_id="agent_decision:nonexistent",
            lesson_id="lesson-01",
            challenge_type="contradicts",
        )

        assert result["success"] is False
        assert "Decision not found" in result["error"]

    def test_record_challenge_lesson_not_found(self, mock_db, reasoning_ops):
        """Test challenge when lesson doesn't exist."""
        mock_db.set_response(
            "SELECT id FROM agent_decision", [{"id": "agent_decision:test"}]
        )
        mock_db.set_response("SELECT id FROM lesson", [])

        result = reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="nonexistent",
            challenge_type="contradicts",
        )

        assert result["success"] is False
        assert "Lesson not found" in result["error"]

    def test_record_challenge_all_types(self, mock_db, reasoning_ops):
        """Test all valid challenge types."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        types = ["contradicts", "limits", "refines", "extends"]

        for challenge_type in types:
            result = reasoning_ops.record_challenge(
                decision_id="agent_decision:test",
                lesson_id="lesson-01",
                challenge_type=challenge_type,
            )
            assert result["success"] is True
            assert result["challenge_type"] == challenge_type

    def test_record_challenge_all_severities(self, mock_db, reasoning_ops):
        """Test all valid severity levels."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        severities = ["major", "minor", "clarification"]

        for severity in severities:
            result = reasoning_ops.record_challenge(
                decision_id="agent_decision:test",
                lesson_id="lesson-01",
                challenge_type="contradicts",
                severity=severity,
            )
            assert result["success"] is True
            assert result["severity"] == severity


class TestRecordCascade:
    """Tests for record_cascade tool."""

    def test_record_cascade_success(self, mock_db, reasoning_ops):
        """Test successful cascade edge creation."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:dependent",
            dependency_type="blocks",
            impact_level="critical",
            notes="Changing this decision requires rework of dependent decision",
        )

        assert result["success"] is True
        assert result["source_decision_id"] == "agent_decision:source"
        assert result["dependent_decision_id"] == "agent_decision:dependent"
        assert result["dependency_type"] == "blocks"
        assert result["impact_level"] == "critical"
        assert "edge_id" in result
        assert "timestamp" in result

    def test_record_cascade_invalid_type(self, reasoning_ops):
        """Test cascade with invalid dependency_type."""
        result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:dependent",
            dependency_type="invalid_type",
        )

        assert result["success"] is False
        assert "Invalid dependency_type" in result["error"]

    def test_record_cascade_invalid_impact(self, reasoning_ops):
        """Test cascade with invalid impact_level."""
        result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:dependent",
            dependency_type="blocks",
            impact_level="invalid_impact",
        )

        assert result["success"] is False
        assert "Invalid impact_level" in result["error"]

    def test_record_cascade_source_not_found(self, mock_db, reasoning_ops):
        """Test cascade when source decision doesn't exist."""

        # Set up responses: source check returns empty, dependent check returns success
        def response_handler(query):
            if "agent_decision:nonexistent" in query:
                return []
            return [{"id": "test:success"}]

        mock_db._execute_query = MagicMock(side_effect=response_handler)

        result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:nonexistent",
            dependent_decision_id="agent_decision:dependent",
            dependency_type="blocks",
        )

        assert result["success"] is False
        assert "Source decision not found" in result["error"]

    def test_record_cascade_dependent_not_found(self, mock_db, reasoning_ops):
        """Test cascade when dependent decision doesn't exist."""

        # Set up responses: source check returns success, dependent check returns empty
        def response_handler(query):
            if "agent_decision:nonexistent" in query:
                return []
            return [{"id": "test:success"}]

        mock_db._execute_query = MagicMock(side_effect=response_handler)

        result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:nonexistent",
            dependency_type="blocks",
        )

        assert result["success"] is False
        assert "Dependent decision not found" in result["error"]

    def test_record_cascade_all_types(self, mock_db, reasoning_ops):
        """Test all valid dependency types."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        types = ["blocks", "enables", "refines", "contradicts"]

        for dependency_type in types:
            result = reasoning_ops.record_cascade(
                source_decision_id="agent_decision:source",
                dependent_decision_id="agent_decision:dependent",
                dependency_type=dependency_type,
            )
            assert result["success"] is True
            assert result["dependency_type"] == dependency_type

    def test_record_cascade_all_impacts(self, mock_db, reasoning_ops):
        """Test all valid impact levels."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        impacts = ["critical", "significant", "minor"]

        for impact_level in impacts:
            result = reasoning_ops.record_cascade(
                source_decision_id="agent_decision:source",
                dependent_decision_id="agent_decision:dependent",
                dependency_type="blocks",
                impact_level=impact_level,
            )
            assert result["success"] is True
            assert result["impact_level"] == impact_level


class TestErrorHandling:
    """Tests for error handling across all tools."""

    def test_exception_handling_reasoning(self, mock_db, reasoning_ops):
        """Test exception handling in record_reasoning."""
        mock_db._execute_query = MagicMock(side_effect=Exception("Database error"))

        result = reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step 1"],
            confidence_score=0.7,
        )

        assert result["success"] is False
        assert "Database error" in result["error"]

    def test_exception_handling_challenge(self, mock_db, reasoning_ops):
        """Test exception handling in record_challenge."""
        mock_db._execute_query = MagicMock(side_effect=Exception("Database error"))

        result = reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="lesson-01",
            challenge_type="contradicts",
        )

        assert result["success"] is False
        assert "Database error" in result["error"]

    def test_exception_handling_cascade(self, mock_db, reasoning_ops):
        """Test exception handling in record_cascade."""
        mock_db._execute_query = MagicMock(side_effect=Exception("Database error"))

        result = reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:dependent",
            dependency_type="blocks",
        )

        assert result["success"] is False
        assert "Database error" in result["error"]


class TestQueryGeneration:
    """Tests for proper SurrealDB query generation."""

    def test_reasoning_query_structure(self, mock_db, reasoning_ops):
        """Test that record_reasoning generates valid SurrealDB queries."""
        mock_db.set_response("SELECT id FROM", [{"id": "agent_decision:test"}])

        reasoning_ops.record_reasoning(
            decision_id="agent_decision:test",
            reasoning_type="research",
            reasoning_chain=["Step 1", "Step 2"],
            confidence_score=0.8,
            assumptions=["Assumption 1"],
            alternatives_rejected=[{"option": "Alt", "reason": "No good"}],
        )

        # Verify CREATE query was executed
        create_queries = [q for q in mock_db.queries if "CREATE agent_reasoning" in q]
        assert len(create_queries) > 0

        create_query = create_queries[0]
        assert "reasoning_id" in create_query
        assert "decision_id" in create_query
        assert "research" in create_query
        assert "0.8" in create_query

    def test_challenge_query_structure(self, mock_db, reasoning_ops):
        """Test that record_challenge generates valid SurrealDB queries."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        reasoning_ops.record_challenge(
            decision_id="agent_decision:test",
            lesson_id="lesson-01",
            challenge_type="contradicts",
            severity="major",
            notes="Test note",
        )

        # Verify RELATE query was executed
        relate_queries = [
            q for q in mock_db.queries if "RELATE" in q and "challenges_lesson" in q
        ]
        assert len(relate_queries) > 0

        relate_query = relate_queries[0]
        assert "agent_decision:test" in relate_query
        assert "lesson-01" in relate_query
        assert "contradicts" in relate_query
        assert "major" in relate_query

    def test_cascade_query_structure(self, mock_db, reasoning_ops):
        """Test that record_cascade generates valid SurrealDB queries."""
        mock_db.set_response("SELECT id FROM", [{"id": "test:success"}])

        reasoning_ops.record_cascade(
            source_decision_id="agent_decision:source",
            dependent_decision_id="agent_decision:dependent",
            dependency_type="blocks",
            impact_level="critical",
            notes="Test cascade",
        )

        # Verify RELATE query was executed
        relate_queries = [
            q for q in mock_db.queries if "RELATE" in q and "relates_to_decision" in q
        ]
        assert len(relate_queries) > 0

        relate_query = relate_queries[0]
        assert "agent_decision:source" in relate_query
        assert "agent_decision:dependent" in relate_query
        assert "blocks" in relate_query
        assert "critical" in relate_query
