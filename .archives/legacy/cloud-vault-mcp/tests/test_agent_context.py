"""Unit tests for agent context operations (Phase 1)."""

from unittest.mock import MagicMock

import pytest

from mcp_server.agent_context import AgentContextOps


class TestAgentContextOps:
    """Tests for agent context tracking, decisions, and outcomes."""

    @pytest.fixture
    def mock_surrealdb(self):
        """Create a mock SurrealDB instance."""
        mock_db = MagicMock()
        mock_db._execute_query = MagicMock()
        return mock_db

    @pytest.fixture
    def agent_context(self, mock_surrealdb):
        """Create an AgentContextOps instance with mocked DB."""
        return AgentContextOps(mock_surrealdb)

    # ── track_session tests ──────────────────────────────────────────

    def test_track_session_success(self, agent_context, mock_surrealdb):
        """Test successful session creation."""
        mock_surrealdb._execute_query.return_value = [
            {
                "id": "agent_session:test-id",
                "agent_id": "test-agent",
                "status": "in_progress",
            }
        ]

        result = agent_context.track_session(
            agent_id="test-agent",
            goals=["goal1", "goal2"],
            model_used="claude-haiku-4-5",
            phase="research",
        )

        assert result["success"] is True
        assert "session_id" in result
        assert result["agent_id"] == "test-agent"
        assert result["status"] == "in_progress"

    def test_track_session_failure(self, agent_context, mock_surrealdb):
        """Test session creation failure."""
        mock_surrealdb._execute_query.return_value = []

        result = agent_context.track_session(
            agent_id="test-agent",
            goals=["goal1"],
        )

        assert result["success"] is False
        assert "error" in result

    def test_track_session_exception(self, agent_context, mock_surrealdb):
        """Test exception handling during session creation."""
        mock_surrealdb._execute_query.side_effect = Exception("DB error")

        result = agent_context.track_session(
            agent_id="test-agent",
            goals=["goal1"],
        )

        assert result["success"] is False
        assert "DB error" in result["error"]

    # ── record_decision tests ────────────────────────────────────────

    def test_record_decision_success(self, agent_context, mock_surrealdb):
        """Test successful decision recording."""
        session_id = "agent_session:test-session"

        # Mock session check
        mock_surrealdb._execute_query.side_effect = [
            [{"id": session_id}],  # session check
            [{"id": "agent_decision:test-decision"}],  # decision creation
            [{"id": "paper:p1"}],  # paper 1 check
            [{"id": "edge:1"}],  # paper 1 link
            [{"id": "paper:p2"}],  # paper 2 check
            [{"id": "edge:2"}],  # paper 2 link
        ]

        result = agent_context.record_decision(
            session_id=session_id,
            decision_type="architecture",
            reasoning="Use SurrealDB for graphs",
            papers_applied=["p1", "p2"],
            confidence_score=0.9,
        )

        assert result["success"] is True
        assert result["decision_type"] == "architecture"
        assert result["confidence_score"] == 0.9
        assert result["links_created"] == 2

    def test_record_decision_missing_session(self, agent_context, mock_surrealdb):
        """Test decision recording when session doesn't exist."""
        mock_surrealdb._execute_query.return_value = []

        result = agent_context.record_decision(
            session_id="agent_session:nonexistent",
            decision_type="architecture",
            reasoning="test",
            papers_applied=["p1"],
        )

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_record_decision_partial_paper_links(self, agent_context, mock_surrealdb):
        """Test decision with some missing papers."""
        session_id = "agent_session:test-session"

        # Mock: session check, decision creation, paper 1 check/link, paper 2 missing
        mock_surrealdb._execute_query.side_effect = [
            [{"id": session_id}],  # session check
            [{"id": "agent_decision:test"}],  # decision creation
            [{"id": "paper:p1"}],  # paper 1 check
            [{"id": "edge:1"}],  # paper 1 link
            [],  # paper 2 check (not found)
        ]

        result = agent_context.record_decision(
            session_id=session_id,
            decision_type="feature",
            reasoning="test",
            papers_applied=["p1", "p2"],
        )

        assert result["success"] is True
        assert result["links_created"] == 1
        assert "validation_warnings" in result

    # ── record_outcome tests ─────────────────────────────────────────

    def test_record_outcome_success(self, agent_context, mock_surrealdb):
        """Test successful outcome recording."""
        session_id = "agent_session:test-session"

        mock_surrealdb._execute_query.side_effect = [
            [{"id": session_id}],  # session check
            [{"id": "agent_outcome:test"}],  # outcome creation
            [{"id": "lesson:l1"}],  # lesson 1 check
            [{"id": "edge:1"}],  # lesson 1 link
            [{"id": "lesson:l2"}],  # lesson 2 check
            [{"id": "edge:2"}],  # lesson 2 link
        ]

        result = agent_context.record_outcome(
            session_id=session_id,
            outcome_type="success",
            lessons_learned=["l1", "l2"],
            metrics={"session_duration_min": 45, "token_efficiency_ratio": 3.2},
        )

        assert result["success"] is True
        assert result["outcome_type"] == "success"
        assert result["validated_lessons"] == 2

    def test_record_outcome_missing_session(self, agent_context, mock_surrealdb):
        """Test outcome recording when session doesn't exist."""
        mock_surrealdb._execute_query.return_value = []

        result = agent_context.record_outcome(
            session_id="agent_session:nonexistent",
            outcome_type="success",
            lessons_learned=["l1"],
        )

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_record_outcome_partial_lessons(self, agent_context, mock_surrealdb):
        """Test outcome with some missing lessons."""
        session_id = "agent_session:test-session"

        mock_surrealdb._execute_query.side_effect = [
            [{"id": session_id}],  # session check
            [{"id": "agent_outcome:test"}],  # outcome creation
            [{"id": "lesson:l1"}],  # lesson 1 check
            [{"id": "edge:1"}],  # lesson 1 link
            [],  # lesson 2 check (not found)
        ]

        result = agent_context.record_outcome(
            session_id=session_id,
            outcome_type="partial",
            lessons_learned=["l1", "l2"],
        )

        assert result["success"] is True
        assert result["validated_lessons"] == 1
        assert "validation_errors" in result

    def test_record_outcome_exception(self, agent_context, mock_surrealdb):
        """Test exception handling during outcome recording."""
        mock_surrealdb._execute_query.side_effect = Exception("DB error")

        result = agent_context.record_outcome(
            session_id="agent_session:test",
            outcome_type="success",
            lessons_learned=["l1"],
        )

        assert result["success"] is False
        assert "DB error" in result["error"]

    # ── Integration tests ────────────────────────────────────────────

    def test_full_workflow(self, agent_context, mock_surrealdb):
        """Test full workflow: session → decision → outcome."""
        session_id = "agent_session:workflow-test"

        # Track session
        mock_surrealdb._execute_query.return_value = [
            {"id": session_id, "status": "in_progress"}
        ]

        session_result = agent_context.track_session(
            agent_id="test-agent",
            goals=["design-schema"],
        )
        assert session_result["success"] is True

        # Record decision
        mock_surrealdb._execute_query.side_effect = [
            [{"id": session_id}],  # session check
            [{"id": "agent_decision:d1"}],  # decision creation
            [{"id": "paper:p1"}],  # paper check
            [{"id": "edge:1"}],  # paper link
        ]

        decision_result = agent_context.record_decision(
            session_id=session_id,
            decision_type="architecture",
            reasoning="Use SurrealDB",
            papers_applied=["p1"],
        )
        assert decision_result["success"] is True
        assert decision_result["links_created"] == 1

        # Record outcome
        mock_surrealdb._execute_query.side_effect = [
            [{"id": session_id}],  # session check
            [{"id": "agent_outcome:o1"}],  # outcome creation
            [{"id": "lesson:l1"}],  # lesson check
            [{"id": "edge:2"}],  # lesson link
        ]

        outcome_result = agent_context.record_outcome(
            session_id=session_id,
            outcome_type="success",
            lessons_learned=["l1"],
        )
        assert outcome_result["success"] is True
        assert outcome_result["validated_lessons"] == 1
