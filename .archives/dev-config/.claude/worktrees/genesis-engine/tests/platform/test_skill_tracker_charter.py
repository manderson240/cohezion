"""
Tests for Charter-Aligned Skill Effectiveness Tracker.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from cohezion.platform.coherence_tracker import CoherenceMetrics
from cohezion.platform.skill_analytics_charter import (
    CharterAlignedSkillAnalytics,
    get_skill_analytics,
    reset_skill_analytics,
)
from cohezion.platform.skill_scorer_charter import (
    CharterAlignedSkillScorer,
    get_skill_scorer,
    reset_skill_scorer,
)
from cohezion.platform.skill_tracker_charter import (
    CharterAlignedSkillTracker,
    SkillUsageEvent,
    get_skill_tracker,
    reset_skill_tracker,
)


@pytest.fixture
def mock_surreal_client():
    """Mock SurrealDB client."""
    mock_client = AsyncMock()
    mock_client.query = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def mock_coherence_tracker():
    """Mock CoherenceTracker."""
    mock_tracker = AsyncMock()
    mock_tracker.measure_system_coherence = AsyncMock(
        return_value=CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=0.8,
            external_alignment=0.7,
            coherence=0.5,
            hiho_stable=True,
            hiho_delta=0.0,
            stability_score=1.0,
        )
    )
    return mock_tracker


@pytest.fixture
def mock_journey_logger():
    """Mock JourneyLogger."""
    mock_logger = AsyncMock()
    mock_logger.extract_learning = AsyncMock()
    return mock_logger


@pytest.fixture
def mock_vae_encoder():
    """Mock FLUME VAE encoder."""
    mock_encoder = MagicMock()
    mock_encoder.encode = MagicMock(return_value=np.zeros(256))
    return mock_encoder


@pytest.fixture
def skill_tracker(mock_surreal_client, mock_coherence_tracker, mock_journey_logger, mock_vae_encoder):
    """Create CharterAlignedSkillTracker with mocked dependencies."""
    with (
        patch(
            "cohezion.platform.skill_tracker_charter.get_surreal_client",
            return_value=mock_surreal_client,
        ),
        patch(
            "cohezion.platform.skill_tracker_charter.get_coherence_tracker",
            return_value=mock_coherence_tracker,
        ),
        patch(
            "cohezion.platform.skill_tracker_charter.get_journey_logger",
            return_value=mock_journey_logger,
        ),
        patch(
            "cohezion.platform.skill_tracker_charter.get_encoder",
            return_value=mock_vae_encoder,
        ),
    ):
        tracker = CharterAlignedSkillTracker()
        yield tracker


@pytest.fixture
def skill_scorer(mock_surreal_client):
    """Create CharterAlignedSkillScorer with mocked dependencies."""
    with patch(
        "cohezion.platform.skill_scorer_charter.get_surreal_client",
        return_value=mock_surreal_client,
    ):
        scorer = CharterAlignedSkillScorer()
        yield scorer


class TestSkillUsageEvent:
    """Test SkillUsageEvent model."""

    def test_skill_usage_event_creation(self):
        """Test creating SkillUsageEvent."""
        event = SkillUsageEvent(
            skill_name="test_skill",
            invoked_at=datetime.now(),
            execution_id="exec-123",
            tokens_used=100,
            success=True,
            latency_ms=250.5,
            coherence_score=0.5,
            hiho_stable=True,
            flume_state=[0.1] * 256,
        )

        assert event.skill_name == "test_skill"
        assert event.tokens_used == 100
        assert event.success is True
        assert event.coherence_score == 0.5
        assert event.hiho_stable is True
        assert len(event.flume_state) == 256


class TestCharterAlignedSkillTracker:
    """Test CharterAlignedSkillTracker class."""

    def test_initialization(self, skill_tracker):
        """Test CharterAlignedSkillTracker initialization."""
        assert skill_tracker.db is not None
        assert skill_tracker.coherence_tracker is not None
        assert skill_tracker.journey_logger is not None
        assert skill_tracker.vae is not None

    @pytest.mark.asyncio
    async def test_log_skill_usage_hiho_stable(self, skill_tracker, mock_surreal_client):
        """Test logging skill usage that is HIHO stable."""
        event = SkillUsageEvent(
            skill_name="test_skill",
            invoked_at=datetime.now(),
            execution_id="exec-123",
            tokens_used=100,
            success=True,
            latency_ms=250.5,
            coherence_score=0.5,  # HIHO stable (0.4-0.6)
            hiho_stable=False,  # Will be updated
            flume_state=[0.1] * 256,
        )

        await skill_tracker.log_skill_usage(event, journey_id="journey-123")

        # Verify HIHO stable was set correctly
        assert event.hiho_stable is True

        # Verify DB query was called
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "CREATE skill_usage" in call_args[0][0]
        assert call_args[0][1]["hiho_stable"] is True

    @pytest.mark.asyncio
    async def test_log_skill_usage_hiho_unstable(self, skill_tracker, mock_surreal_client, mock_journey_logger):
        """Test logging skill usage that is HIHO unstable."""
        event = SkillUsageEvent(
            skill_name="test_skill",
            invoked_at=datetime.now(),
            execution_id="exec-123",
            tokens_used=100,
            success=True,
            latency_ms=250.5,
            coherence_score=0.9,  # HIHO unstable (>0.6)
            hiho_stable=False,
            flume_state=[0.1] * 256,
        )

        await skill_tracker.log_skill_usage(event, journey_id="journey-123")

        # Verify HIHO unstable
        assert event.hiho_stable is False

        # Verify learning was extracted
        mock_journey_logger.extract_learning.assert_called_once_with(
            journey_id="journey-123",
            learning="Skill test_skill executed outside HIHO range: 0.900",
            pattern_type="hiho_violation",
        )

    @pytest.mark.asyncio
    async def test_create_skill_usage_event(self, skill_tracker, mock_vae_encoder):
        """Test creating skill usage event with coherence calculation."""
        event = await skill_tracker.create_skill_usage_event(
            skill_name="test_skill",
            tokens_used=100,
            success=True,
            latency_ms=250.5,
            coherence_before=0.5,
            coherence_after=0.55,  # Small change
            prompt="Test prompt",
        )

        # Execution coherence = 1.0 - abs(0.55 - 0.5) = 0.95
        assert 0.94 <= event.coherence_score <= 0.96
        assert event.success is True
        assert event.tokens_used == 100
        assert len(event.flume_state) == 256

        # Verify VAE was called
        mock_vae_encoder.encode.assert_called_once_with("Test prompt")


class TestCharterAlignedSkillScorer:
    """Test CharterAlignedSkillScorer class."""

    def test_initialization(self, skill_scorer):
        """Test CharterAlignedSkillScorer initialization."""
        assert skill_scorer.db is not None
        assert skill_scorer.target_coherence == 0.5

    @pytest.mark.asyncio
    async def test_calculate_daily_scores(self, skill_scorer, mock_surreal_client):
        """Test calculating Charter-aligned daily scores."""
        # Mock query result
        mock_surreal_client.query.return_value = [
            {
                "skill_name": "skill_A",
                "usage_count": 10,
                "total_tokens": 1000,
                "success_count": 9,
                "avg_coherence": 0.5,  # Perfect HIHO
                "hiho_stable_count": 10,
            }
        ]

        scores = await skill_scorer.calculate_daily_scores(datetime.now())

        assert len(scores) == 1
        score = scores[0]

        # Verify Charter-aligned scoring
        assert score.skill_name == "skill_A"
        assert score.success_rate == 0.9  # 9/10
        assert score.hiho_stability == 1.0  # Perfect 0.5
        # Effectiveness = 0.5*1.0 + 0.25*0.9 + 0.25*0.009 = 0.725
        assert 0.72 <= score.effectiveness_score <= 0.73

    @pytest.mark.asyncio
    async def test_hiho_stability_calculation(self, skill_scorer):
        """Test HIHO stability calculation."""
        # Perfect HIHO (0.5)
        hiho_delta = abs(0.5 - skill_scorer.target_coherence)
        hiho_stability = max(0.0, 1.0 - (hiho_delta * 2))
        assert hiho_stability == 1.0

        # Slightly off (0.6)
        hiho_delta = abs(0.6 - skill_scorer.target_coherence)
        hiho_stability = max(0.0, 1.0 - (hiho_delta * 2))
        assert hiho_stability == 0.8

        # Far off (0.9)
        hiho_delta = abs(0.9 - skill_scorer.target_coherence)
        hiho_stability = max(0.0, 1.0 - (hiho_delta * 2))
        assert hiho_stability == pytest.approx(0.2)


class TestCharterAlignedSkillAnalytics:
    """Test CharterAlignedSkillAnalytics class."""

    @pytest.fixture
    def mock_edl_router(self):
        """Mock EDL router."""
        from cohezion.platform.edl_router import EDLConsensus

        mock_router = AsyncMock()
        mock_router.route_decision = AsyncMock(
            return_value=EDLConsensus(
                decision="Approve refinement",
                coherence=0.5,
                hiho_stable=True,
                consensus_strength=0.85,
                stream_recommendations=[],
                requires_human_review=False,
                reasoning="Consensus reached",
            )
        )
        return mock_router

    @pytest.fixture
    def mock_observable_proposer(self):
        """Mock observable proposer."""
        mock_proposer = AsyncMock()
        mock_proposer.propose_action = AsyncMock(return_value=True)
        return mock_proposer

    @pytest.fixture
    def skill_analytics(self, mock_surreal_client, mock_edl_router, mock_observable_proposer):
        """Create CharterAlignedSkillAnalytics with mocked dependencies."""
        with (
            patch(
                "cohezion.platform.skill_analytics_charter.get_surreal_client",
                return_value=mock_surreal_client,
            ),
            patch(
                "cohezion.platform.skill_analytics_charter.get_edl_router",
                return_value=mock_edl_router,
            ),
            patch(
                "cohezion.platform.skill_analytics_charter.get_observable_proposer",
                return_value=mock_observable_proposer,
            ),
            patch("cohezion.platform.skill_analytics_charter.get_skill_scorer"),
        ):
            analytics = CharterAlignedSkillAnalytics()
            yield analytics

    @pytest.mark.asyncio
    async def test_generate_insights(self, skill_analytics, mock_surreal_client):
        """Test generating Charter-compliant insights."""
        # Mock query results for different insight types
        mock_surreal_client.query.side_effect = [
            [{"skill_name": "stable_skill_A", "avg_hiho": 0.9}],  # Top HIHO stable
            [{"skill_name": "unstable_skill_B", "avg_coherence": 0.2}],  # HIHO unstable
            [{"skill_name": "failing_skill_C", "avg_success": 0.3}],  # Failing skills
        ]

        insights = await skill_analytics.generate_insights(days=7)

        assert len(insights.top_hiho_stable) == 1
        assert insights.top_hiho_stable[0] == "stable_skill_A"
        assert len(insights.hiho_unstable) == 1
        assert insights.hiho_unstable[0] == "unstable_skill_B"
        assert len(insights.failing_skills) == 1
        assert insights.failing_skills[0] == "failing_skill_C"


class TestSingletonAccessors:
    """Test singleton accessor functions."""

    def test_get_skill_tracker(self):
        """Test getting global skill tracker."""
        reset_skill_tracker()

        tracker1 = get_skill_tracker()
        tracker2 = get_skill_tracker()

        assert tracker1 is tracker2

    def test_reset_skill_tracker(self):
        """Test resetting global skill tracker."""
        tracker1 = get_skill_tracker()
        reset_skill_tracker()
        tracker2 = get_skill_tracker()

        assert tracker1 is not tracker2

    def test_get_skill_scorer(self):
        """Test getting global skill scorer."""
        reset_skill_scorer()

        scorer1 = get_skill_scorer()
        scorer2 = get_skill_scorer()

        assert scorer1 is scorer2

    def test_get_skill_analytics(self):
        """Test getting global skill analytics."""
        reset_skill_analytics()

        analytics1 = get_skill_analytics()
        analytics2 = get_skill_analytics()

        assert analytics1 is analytics2
