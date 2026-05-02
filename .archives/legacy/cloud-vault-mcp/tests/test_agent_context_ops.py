"""Tests for AgentContextOps - agent execution context tracking.

Tests the SurrealDB integration for sessions, decisions, actions, outcomes, and lessons.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest


logger = logging.getLogger(__name__)


# Mock SurrealDB responses for testing
class MockSurrealDBSync:
    """Mock SurrealDB sync for testing."""

    def __init__(self):
        self.queries = []

    def execute_query(self, query: str):
        """Record query for inspection."""
        self.queries.append(query)
        return [{"result": "ok"}]


@pytest.fixture
def agent_context_ops():
    """Create AgentContextOps instance with mocked HTTP client."""
    from mcp_server.agent_context_ops import AgentContextOps

    with patch("mcp_server.agent_context_ops.httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock successful responses
        mock_response = MagicMock()
        mock_response.json.return_value = [{"result": "ok"}]
        mock_client.post.return_value = mock_response

        ops = AgentContextOps()
        ops.client = mock_client
        yield ops


class TestTrackSession:
    """Test session tracking functionality."""

    def test_track_session_basic(self, agent_context_ops):
        """Test basic session tracking."""
        session_id = agent_context_ops.track_session(
            agent_names=["researcher", "implementer"],
            duration_ms=5000,
            status="completed",
        )

        assert session_id.startswith("session:")
        assert agent_context_ops.client.post.called

    def test_track_session_with_error(self, agent_context_ops):
        """Test session tracking with error message."""
        session_id = agent_context_ops.track_session(
            agent_names=["implementer"],
            duration_ms=2000,
            status="error",
            error_message="Connection timeout",
        )

        assert session_id.startswith("session:")
        # Verify error_message was included in query
        call_args = agent_context_ops.client.post.call_args
        query_content = call_args.kwargs.get("content")
        assert "Connection timeout" in query_content

    def test_track_session_with_metrics(self, agent_context_ops):
        """Test session tracking with execution metrics."""
        session_id = agent_context_ops.track_session(
            agent_names=["researcher", "implementer", "tester"],
            duration_ms=15000,
            status="completed",
            model_used="sonnet",
            total_turns=47,
            total_functions=312,
        )

        assert session_id.startswith("session:")
        call_args = agent_context_ops.client.post.call_args
        query_content = call_args.kwargs.get("content")
        assert "47" in query_content  # total_turns
        assert "312" in query_content  # total_functions


class TestRecordDecision:
    """Test decision recording functionality."""

    def test_record_decision_basic(self, agent_context_ops):
        """Test basic decision recording."""
        decision_id = agent_context_ops.record_decision(
            session_id="session:abc123",
            title="Use SurrealDB for graph storage",
            context="Need to store complex relationships between vault notes",
            reasoning="SurrealDB provides native graph edges and flexible schema",
            alternatives=["Neo4j", "PostgreSQL with custom schema"],
            chosen_path="SurrealDB",
        )

        assert decision_id.startswith("decision:")
        assert agent_context_ops.client.post.called

    def test_record_decision_with_confidence(self, agent_context_ops):
        """Test decision recording with confidence score."""
        decision_id = agent_context_ops.record_decision(
            session_id="session:abc123",
            title="Refactor vault ops",
            context="Current code is duplicated",
            reasoning="DRY principle",
            alternatives=["Keep as-is", "Extract shared methods"],
            chosen_path="Extract shared methods",
            confidence=0.95,
            reversible=True,
        )

        assert decision_id.startswith("decision:")
        call_args = agent_context_ops.client.post.call_args
        query_content = call_args.kwargs.get("content")
        assert "0.95" in query_content
        assert "has_decisions" in query_content  # Should link to session

    def test_record_decision_irreversible(self, agent_context_ops):
        """Test recording an irreversible decision."""
        decision_id = agent_context_ops.record_decision(
            session_id="session:abc123",
            title="Delete old schema",
            context="Schema v1 no longer needed",
            reasoning="Cleaned up migrations",
            alternatives=["Archive instead of delete"],
            chosen_path="Delete",
            reversible=False,
        )

        assert decision_id.startswith("decision:")


class TestRecordAction:
    """Test action recording functionality."""

    def test_record_action_success(self, agent_context_ops):
        """Test recording successful action."""
        action_id = agent_context_ops.record_action(
            session_id="session:abc123",
            tool_name="vault_write",
            input_params={"path": "decisions/2026-02-11-test.md"},
            output="Note created successfully",
            duration_ms=250,
            status="success",
        )

        assert action_id.startswith("action:")
        assert agent_context_ops.client.post.called

    def test_record_action_with_error(self, agent_context_ops):
        """Test recording failed action."""
        action_id = agent_context_ops.record_action(
            session_id="session:abc123",
            tool_name="bash",
            input_params={"command": "curl http://localhost:8001/sql"},
            output="",
            duration_ms=5000,
            status="timeout",
            error_details="Connection timeout after 5000ms",
        )

        assert action_id.startswith("action:")
        call_args = agent_context_ops.client.post.call_args
        query_content = call_args.kwargs.get("content")
        assert "timeout" in query_content

    def test_record_action_truncates_long_output(self, agent_context_ops):
        """Test that very long outputs are truncated."""
        long_output = "x" * 10000
        action_id = agent_context_ops.record_action(
            session_id="session:abc123",
            tool_name="bash",
            input_params={"command": "echo test"},
            output=long_output,
            duration_ms=100,
            status="success",
        )

        assert action_id.startswith("action:")
        call_args = agent_context_ops.client.post.call_args
        query_content = call_args.kwargs.get("content")
        # Output should be truncated to 5000 chars
        assert len(long_output) > 5000
        # The actual query should have truncated version
        assert "xxxx" in query_content
        assert query_content.count("x") < len(long_output)


class TestRecordOutcome:
    """Test outcome recording functionality."""

    def test_record_outcome_success(self, agent_context_ops):
        """Test recording successful outcome."""
        outcome_id = agent_context_ops.record_outcome(
            session_id="session:abc123",
            status="success",
            summary="Agent successfully created 3 vault notes and extracted 2 lessons",
            metrics={
                "total_turns": 47,
                "total_functions": 312,
                "errors": 2,
                "recovery_attempts": 1,
            },
            vault_notes_created=[
                "decisions/2026-02-11-example.md",
                "patterns/compound-engineering.md",
            ],
        )

        assert outcome_id.startswith("outcome:")
        assert agent_context_ops.client.post.called

    def test_record_outcome_partial(self, agent_context_ops):
        """Test recording partial outcome."""
        outcome_id = agent_context_ops.record_outcome(
            session_id="session:abc123",
            status="partial",
            summary="Completed task A, failed on task B (need manual review)",
            metrics={
                "total_turns": 32,
                "total_functions": 215,
                "errors": 3,
            },
            artifacts=[
                "/tmp/export.json",
                "/tmp/analysis.csv",
            ],
        )

        assert outcome_id.startswith("outcome:")


class TestRecordLesson:
    """Test lesson recording functionality."""

    def test_record_lesson_auto_extracted(self, agent_context_ops):
        """Test auto-extracted lesson."""
        lesson_id = agent_context_ops.record_lesson(
            session_id="session:abc123",
            title="Use batch operations for database updates",
            severity="HIGH",
            description="Updating 100 rows one at a time is 10x slower than batch update",
            auto_extracted=True,
        )

        assert lesson_id.startswith("lesson:")

    def test_record_lesson_with_vault_link(self, agent_context_ops):
        """Test lesson with vault link."""
        lesson_id = agent_context_ops.record_lesson(
            session_id="session:abc123",
            title="Implementation-first methodology",
            severity="CRITICAL",
            description="Always validate concept with minimal code before scaling",
            linked_lesson_path="lessons/2026-02-11-implementation-first.md",
            auto_extracted=False,
        )

        assert lesson_id.startswith("lesson:")
        call_args = agent_context_ops.client.post.call_args
        query_content = call_args.kwargs.get("content")
        assert "lessons/2026-02-11-implementation-first.md" in query_content


class TestQueryMethods:
    """Test complex query functionality."""

    def test_query_research_lineage(self, agent_context_ops):
        """Test research lineage query."""
        # Mock query response
        agent_context_ops.client.post.return_value = MagicMock(
            json=lambda: [
                {
                    "paper": "papers/surrealdb-overview",
                    "title": "Use graph database for relationships",
                    "source_type": "paper",
                },
                {
                    "paper": "papers/schema-design",
                    "title": "Normalize schema for query efficiency",
                    "source_type": "paper",
                },
            ]
        )

        results = agent_context_ops.query_research_lineage("session:abc123")

        assert len(results) == 2
        assert results[0]["paper"] == "papers/surrealdb-overview"

    def test_query_lesson_validation(self, agent_context_ops):
        """Test lesson validation query."""
        # Mock query response
        agent_context_ops.client.post.return_value = MagicMock(
            json=lambda: [
                {
                    "lesson": "lesson:batch-operations",
                    "status": "success",
                    "severity": "HIGH",
                    "linked_lesson_path": "lessons/2026-02-11-batch-ops.md",
                }
            ]
        )

        results = agent_context_ops.query_lesson_validation("session:abc123")

        assert len(results) == 1
        assert results[0]["lesson"] == "lesson:batch-operations"
        assert results[0]["severity"] == "HIGH"

    def test_query_cascading_impact(self, agent_context_ops):
        """Test cascading impact query."""
        # Mock query response
        agent_context_ops.client.post.return_value = MagicMock(
            json=lambda: [
                {
                    "id": "decision:use-surrealdb",
                    "title": "Use SurrealDB",
                    "reasoning": "Native graph support",
                    "chosen_path": "SurrealDB",
                    "informed_actions": [
                        "action:create-schema",
                        "action:write-ops",
                        "action:write-tests",
                    ],
                }
            ]
        )

        result = agent_context_ops.query_cascading_impact("decision:use-surrealdb")

        assert result["id"] == "decision:use-surrealdb"
        assert len(result["informed_actions"]) == 3


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_track_session_http_error(self, agent_context_ops):
        """Test handling of HTTP errors."""
        agent_context_ops.client.post.side_effect = Exception("Connection refused")

        with pytest.raises(Exception):  # noqa: B017
            agent_context_ops.track_session(
                agent_names=["test"],
                duration_ms=1000,
                status="error",
            )

    def test_record_decision_empty_alternatives(self, agent_context_ops):
        """Test decision with empty alternatives list."""
        decision_id = agent_context_ops.record_decision(
            session_id="session:abc123",
            title="No choice available",
            context="Only one path possible",
            reasoning="Forced choice",
            alternatives=[],  # Empty alternatives
            chosen_path="The only option",
        )

        assert decision_id.startswith("decision:")

    def test_record_action_empty_params(self, agent_context_ops):
        """Test action with empty parameters."""
        action_id = agent_context_ops.record_action(
            session_id="session:abc123",
            tool_name="health_check",
            input_params={},  # Empty
            output="System healthy",
            duration_ms=100,
        )

        assert action_id.startswith("action:")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
