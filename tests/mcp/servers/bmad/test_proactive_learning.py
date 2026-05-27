"""Tests for Proactive Monitor Learning System - Phase 5.

Tests acceptance tracking, confidence adjustment, and feedback collection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.core.persistence.repositories.surreal_proactive_repository import (
    PatternEffectiveness,
    SuggestionAcceptance,
    SurrealProactiveRepository,
)
from cohezion.mcp.servers.bmad.proactive_monitor import ProactiveMonitor, ProactiveSuggestion


pytestmark = [pytest.mark.fast]  # asyncio applied per-test on async methods only


class TestSuggestionAcceptance:
    """Tests for SuggestionAcceptance dataclass."""

    @pytest.mark.fast
    def test_acceptance_creation(self):
        """Test SuggestionAcceptance creation."""
        acceptance = SuggestionAcceptance(
            suggestion_id="test-suggestion",
            pattern_id="test-pattern",
            accepted=True,
            feedback="Very helpful!",
            user_id="test-user",
            confidence_at_decision=0.9,
        )

        assert acceptance.suggestion_id == "test-suggestion"
        assert acceptance.pattern_id == "test-pattern"
        assert acceptance.accepted is True
        assert acceptance.feedback == "Very helpful!"
        assert acceptance.user_id == "test-user"
        assert acceptance.confidence_at_decision == 0.9
        assert acceptance.timestamp != ""  # Auto-generated

    @pytest.mark.fast
    def test_acceptance_with_execution_time(self):
        """Test SuggestionAcceptance with execution time."""
        acceptance = SuggestionAcceptance(
            suggestion_id="test-suggestion",
            pattern_id="test-pattern",
            accepted=True,
            execution_time_ms=1250.5,
        )

        assert acceptance.execution_time_ms == 1250.5


class TestPatternEffectiveness:
    """Tests for PatternEffectiveness dataclass."""

    @pytest.mark.fast
    def test_effectiveness_creation(self):
        """Test PatternEffectiveness creation."""
        effectiveness = PatternEffectiveness(
            pattern_id="test-pattern",
            pattern_name="Test Pattern",
            total_suggestions=100,
            accepted=80,
            rejected=20,
            avg_confidence=0.85,
        )

        assert effectiveness.pattern_id == "test-pattern"
        assert effectiveness.total_suggestions == 100
        assert effectiveness.accepted == 80
        assert effectiveness.rejected == 20
        assert effectiveness.avg_confidence == 0.85

    @pytest.mark.fast
    def test_acceptance_rate_calculation(self):
        """Test acceptance rate calculation."""
        effectiveness = PatternEffectiveness(
            pattern_id="test-pattern",
            pattern_name="Test Pattern",
            total_suggestions=100,
            accepted=80,
            rejected=20,
        )

        assert effectiveness.acceptance_rate == 0.8

    @pytest.mark.fast
    def test_acceptance_rate_zero_suggestions(self):
        """Test acceptance rate with zero suggestions."""
        effectiveness = PatternEffectiveness(
            pattern_id="test-pattern",
            pattern_name="Test Pattern",
            total_suggestions=0,
            accepted=0,
            rejected=0,
        )

        assert effectiveness.acceptance_rate == 0.0

    @pytest.mark.fast
    def test_effectiveness_score_calculation(self):
        """Test effectiveness score calculation (weighted)."""
        effectiveness = PatternEffectiveness(
            pattern_id="test-pattern",
            pattern_name="Test Pattern",
            total_suggestions=100,
            accepted=80,
            rejected=20,
            avg_confidence=0.9,
        )

        # effectiveness_score = (acceptance_rate * 0.7) + (avg_confidence * 0.3)
        # = (0.8 * 0.7) + (0.9 * 0.3) = 0.56 + 0.27 = 0.83
        expected_score = (0.8 * 0.7) + (0.9 * 0.3)
        assert abs(effectiveness.effectiveness_score - expected_score) < 0.001


class TestSurrealProactiveRepository:
    """Tests for SurrealProactiveRepository."""

    @pytest.mark.fast
    @patch(
        "cohezion.core.persistence.repositories.surreal_proactive_repository.SurrealProactiveRepository._ensure_table"
    )
    @pytest.mark.asyncio
    async def test_record_acceptance(self, mock_ensure):
        """Test recording acceptance."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(return_value=[{"id": "acceptance_test"}])

        repo = SurrealProactiveRepository(mock_client)

        acceptance = SuggestionAcceptance(
            suggestion_id="test-suggestion",
            pattern_id="test-pattern",
            accepted=True,
            feedback="Great!",
        )

        result = await repo.record_acceptance(acceptance)

        assert mock_client.query.called
        assert result.suggestion_id == "test-suggestion"
        mock_ensure.assert_called_once()

    @pytest.mark.fast
    @patch(
        "cohezion.core.persistence.repositories.surreal_proactive_repository.SurrealProactiveRepository._ensure_table"
    )
    @pytest.mark.asyncio
    async def test_get_pattern_effectiveness(self, mock_ensure):
        """Test getting pattern effectiveness."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(
            return_value=[
                {
                    "pattern_id": "test-pattern",
                    "total_suggestions": 50,
                    "accepted": 40,
                    "rejected": 10,
                    "avg_confidence": 0.85,
                    "avg_execution_time_ms": 1200.0,
                }
            ]
        )

        repo = SurrealProactiveRepository(mock_client)
        effectiveness = await repo.get_pattern_effectiveness("test-pattern")

        assert effectiveness.pattern_id == "test-pattern"
        assert effectiveness.total_suggestions == 50
        assert effectiveness.accepted == 40
        assert effectiveness.acceptance_rate == 0.8

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_get_pattern_effectiveness_no_data(self):
        """Test getting pattern effectiveness with no data."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(return_value=[])

        repo = SurrealProactiveRepository(mock_client)
        effectiveness = await repo.get_pattern_effectiveness("test-pattern")

        assert effectiveness.total_suggestions == 0
        assert effectiveness.acceptance_rate == 0.0


class TestProactiveMonitorLearningSystem:
    """Tests for ProactiveMonitor learning system integration."""

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_monitor_initialization_with_db(self):
        """Test ProactiveMonitor initialization with database."""
        mock_client = MagicMock()
        monitor = ProactiveMonitor(project_root=MagicMock(), db=mock_client)

        assert monitor._repository is not None
        assert isinstance(monitor._repository, SurrealProactiveRepository)

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_monitor_initialization_without_db(self):
        """Test ProactiveMonitor initialization without database."""
        monitor = ProactiveMonitor(project_root=MagicMock())

        assert monitor._repository is None

    @pytest.mark.fast
    @patch(
        "cohezion.core.persistence.repositories.surreal_proactive_repository.SurrealProactiveRepository.record_acceptance"
    )
    @pytest.mark.asyncio
    async def test_record_feedback(self, mock_record):
        """Test recording feedback."""
        mock_client = MagicMock()
        mock_record.return_value = SuggestionAcceptance(
            suggestion_id="test-suggestion",
            pattern_id="test-pattern",
            accepted=True,
        )

        monitor = ProactiveMonitor(project_root=MagicMock(), db=mock_client)

        suggestion = ProactiveSuggestion(
            id="test-suggestion",
            title="Test",
            description="Test",
            priority="high",
            category="alignment",
            suggested_action="Test",
            confidence=0.9,
        )

        acceptance = await monitor.record_feedback(
            suggestion=suggestion,
            accepted=True,
            execution_time_ms=1000.0,
            feedback="Very helpful!",
            user_id="test-user",
        )

        assert acceptance.accepted is True
        assert acceptance.feedback == "Very helpful!"
        mock_record.assert_called_once()

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_record_feedback_without_repository(self):
        """Test recording feedback without repository raises error."""
        monitor = ProactiveMonitor(project_root=MagicMock())

        suggestion = ProactiveSuggestion(
            id="test-suggestion",
            title="Test",
            description="Test",
            priority="high",
            category="alignment",
            suggested_action="Test",
            confidence=0.9,
        )

        with pytest.raises(RuntimeError, match="Learning system not initialized"):
            await monitor.record_feedback(suggestion=suggestion, accepted=True)

    @pytest.mark.fast
    @patch(
        "cohezion.core.persistence.repositories.surreal_proactive_repository.SurrealProactiveRepository.get_pattern_effectiveness"
    )
    @pytest.mark.asyncio
    async def test_adjust_confidence_high_acceptance(self, mock_get_effectiveness):
        """Test confidence adjustment with high acceptance rate."""
        mock_client = MagicMock()
        mock_get_effectiveness.return_value = PatternEffectiveness(
            pattern_id="test-pattern",
            pattern_name="Test Pattern",
            total_suggestions=100,
            accepted=90,
            rejected=10,
            avg_confidence=0.8,
        )

        monitor = ProactiveMonitor(project_root=MagicMock(), db=mock_client)
        new_confidence = await monitor.adjust_pattern_confidence("test-pattern")

        # High acceptance (>0.8) should increase confidence by 5%
        expected = min(1.0, 0.8 * 1.05)
        assert abs(new_confidence - expected) < 0.001

    @pytest.mark.fast
    @patch(
        "cohezion.core.persistence.repositories.surreal_proactive_repository.SurrealProactiveRepository.get_pattern_effectiveness"
    )
    @pytest.mark.asyncio
    async def test_adjust_confidence_low_acceptance(self, mock_get_effectiveness):
        """Test confidence adjustment with low acceptance rate."""
        mock_client = MagicMock()
        mock_get_effectiveness.return_value = PatternEffectiveness(
            pattern_id="test-pattern",
            pattern_name="Test Pattern",
            total_suggestions=100,
            accepted=30,
            rejected=70,
            avg_confidence=0.8,
        )

        monitor = ProactiveMonitor(project_root=MagicMock(), db=mock_client)
        new_confidence = await monitor.adjust_pattern_confidence("test-pattern")

        # Low acceptance (<0.5) should decrease confidence by 10%
        expected = max(0.0, 0.8 * 0.9)
        assert abs(new_confidence - expected) < 0.001

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_adjust_confidence_insufficient_data(self):
        """Test confidence adjustment with insufficient data."""
        mock_client = MagicMock()
        mock_repo = AsyncMock()
        mock_repo.get_pattern_effectiveness = AsyncMock(
            return_value=PatternEffectiveness(
                pattern_id="test-pattern",
                pattern_name="Test Pattern",
                total_suggestions=3,  # Less than 5
                accepted=3,
                rejected=0,
                avg_confidence=0.9,
            )
        )

        monitor = ProactiveMonitor(project_root=MagicMock(), db=mock_client)
        monitor._repository = mock_repo

        new_confidence = await monitor.adjust_pattern_confidence("test-pattern")

        # Should return 0.0 when insufficient data
        assert new_confidence == 0.0

    @pytest.mark.fast
    @patch(
        "cohezion.core.persistence.repositories.surreal_proactive_repository.SurrealProactiveRepository.get_all_pattern_effectiveness"
    )
    @pytest.mark.asyncio
    async def test_get_effectiveness_report(self, mock_get_all):
        """Test getting effectiveness report."""
        mock_client = MagicMock()
        mock_get_all.return_value = [
            PatternEffectiveness(
                pattern_id="pattern-a",
                pattern_name="Pattern A",
                total_suggestions=100,
                accepted=80,
                rejected=20,
                avg_confidence=0.85,
            ),
            PatternEffectiveness(
                pattern_id="pattern-b",
                pattern_name="Pattern B",
                total_suggestions=50,
                accepted=40,
                rejected=10,
                avg_confidence=0.9,
            ),
        ]

        monitor = ProactiveMonitor(project_root=MagicMock(), db=mock_client)
        report = await monitor.get_pattern_effectiveness_report()

        assert len(report) == 2
        # Should be sorted by effectiveness score (descending)
        assert report[0].pattern_id in ["pattern-a", "pattern-b"]

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_get_effectiveness_report_without_repository(self):
        """Test getting effectiveness report without repository raises error."""
        monitor = ProactiveMonitor(project_root=MagicMock())

        with pytest.raises(RuntimeError, match="Learning system not initialized"):
            await monitor.get_pattern_effectiveness_report()

    @pytest.mark.fast
    @patch(
        "cohezion.core.persistence.repositories.surreal_proactive_repository.SurrealProactiveRepository.delete_old_records"
    )
    @pytest.mark.asyncio
    async def test_cleanup_old_records(self, mock_delete):
        """Test cleaning up old records."""
        mock_client = MagicMock()
        mock_delete.return_value = 150

        monitor = ProactiveMonitor(project_root=MagicMock(), db=mock_client)
        deleted = await monitor.cleanup_old_records(days_old=90)

        assert deleted == 150
        mock_delete.assert_called_once_with(90)

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_summary_includes_learning_system_status(self):
        """Test summary includes learning system status."""
        # Without DB
        monitor_no_db = ProactiveMonitor(project_root=MagicMock())
        summary_no_db = monitor_no_db.get_summary()
        assert summary_no_db["learning_system_enabled"] is False

        # With DB
        mock_client = MagicMock()
        monitor_with_db = ProactiveMonitor(project_root=MagicMock(), db=mock_client)
        summary_with_db = monitor_with_db.get_summary()
        assert summary_with_db["learning_system_enabled"] is True


class TestProactiveFeedbackRoutes:
    """Tests for proactive feedback HTTP routes."""

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_record_feedback_route_missing_suggestion_id(self):
        """Test record feedback route with missing suggestion_id."""
        import json

        from cohezion.mcp.servers.bmad.routes_proactive import proactive_record_feedback

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"accepted": True})

        response = await proactive_record_feedback(mock_request)

        assert response.status == 400
        data = json.loads(response.text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_pattern_effectiveness_route_no_database(self):
        """Test pattern effectiveness route without database."""
        import json

        from cohezion.mcp.servers.bmad.routes_proactive import proactive_pattern_effectiveness

        mock_request = MagicMock()
        mock_request.app.get = MagicMock(return_value=None)  # No DB

        response = await proactive_pattern_effectiveness(mock_request)

        assert response.status == 503
        data = json.loads(response.text)
        assert "Learning system not initialized" in data["error"]
