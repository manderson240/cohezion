"""
Tests for JourneyLogger - Journey persistence with FLUME trajectories.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from cohezion.platform.journey_logger import (
    Journey,
    JourneyLogger,
    get_journey_logger,
    reset_journey_logger,
)


@pytest.fixture
def mock_surreal_client():
    """Mock SurrealDB client."""
    mock_client = AsyncMock()
    mock_client.query = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def mock_vae_encoder():
    """Mock FLUME VAE encoder."""
    mock_encoder = MagicMock()
    mock_encoder.encode = MagicMock(return_value=np.zeros(256))  # 256D vector
    return mock_encoder


@pytest.fixture
def mock_coherence_tracker():
    """Mock CoherenceTracker."""
    from cohezion.platform.coherence_tracker import CoherenceMetrics

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
def journey_logger(mock_surreal_client, mock_vae_encoder, mock_coherence_tracker):
    """Create JourneyLogger with mocked dependencies."""
    with (
        patch(
            "cohezion.platform.journey_logger.get_surreal_client",
            return_value=mock_surreal_client,
        ),
        patch(
            "cohezion.platform.journey_logger.get_encoder",
            return_value=mock_vae_encoder,
        ),
        patch(
            "cohezion.platform.journey_logger.get_coherence_tracker",
            return_value=mock_coherence_tracker,
        ),
    ):
        logger = JourneyLogger()
        yield logger


class TestJourney:
    """Test Journey model."""

    def test_journey_creation(self):
        """Test creating Journey."""
        journey = Journey(
            journey_id="test-123",
            journey_type="implementation",
            timestamp=datetime.now(),
            coherence_at_start=0.5,
            coherence_at_end=0.6,
            hiho_stable=True,
            flume_trajectory=[0.1] * 256,
            decisions_made=["Decision 1", "Decision 2"],
            learnings_extracted=["Learning 1"],
            outcome="Success",
            metadata={"key": "value"},
        )

        assert journey.journey_id == "test-123"
        assert journey.journey_type == "implementation"
        assert journey.coherence_at_start == 0.5
        assert journey.coherence_at_end == 0.6
        assert journey.hiho_stable is True
        assert len(journey.flume_trajectory) == 256
        assert len(journey.decisions_made) == 2
        assert len(journey.learnings_extracted) == 1


class TestJourneyLogger:
    """Test JourneyLogger class."""

    def test_initialization(self, journey_logger):
        """Test JourneyLogger initialization."""
        assert journey_logger.db is not None
        assert journey_logger.vae is not None
        assert journey_logger.coherence_tracker is not None

    @pytest.mark.asyncio
    async def test_start_journey(self, journey_logger, mock_surreal_client, mock_vae_encoder):
        """Test starting a journey."""
        journey_id = await journey_logger.start_journey(journey_type="implementation", context="Building new feature")

        assert isinstance(journey_id, str)
        assert len(journey_id) > 0

        # Verify DB query was called
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "CREATE platform_journeys" in call_args[0][0]
        assert call_args[0][1]["journey_type"] == "implementation"

        # Verify VAE encoding was called
        mock_vae_encoder.encode.assert_called_once_with("Building new feature")

    @pytest.mark.asyncio
    async def test_log_decision(self, journey_logger, mock_surreal_client):
        """Test logging a decision during journey."""
        await journey_logger.log_decision(
            journey_id="test-123",
            decision="Use microservices architecture",
            rationale="Better scalability",
        )

        # Verify DB query was called
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "UPDATE platform_journeys" in call_args[0][0]
        assert "decisions_made" in call_args[0][0]
        assert call_args[0][1]["journey_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_extract_learning(self, journey_logger, mock_surreal_client):
        """Test extracting a learning from journey."""
        await journey_logger.extract_learning(
            journey_id="test-123",
            learning="Always validate inputs",
            pattern_type="security",
        )

        # Verify DB query was called
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "UPDATE platform_journeys" in call_args[0][0]
        assert "learnings_extracted" in call_args[0][0]
        assert call_args[0][1]["journey_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_complete_journey(self, journey_logger, mock_surreal_client, mock_vae_encoder):
        """Test completing a journey."""
        # Mock the SELECT query to return journey data
        mock_surreal_client.query.side_effect = [
            [],  # UPDATE query
            [
                {  # SELECT query
                    "journey_id": "test-123",
                    "journey_type": "implementation",
                    "started_at": datetime.now().isoformat(),
                    "coherence_at_start": 0.5,
                    "coherence_at_end": 0.6,
                    "hiho_stable": True,
                    "flume_state_end": [0.1] * 256,
                    "decisions_made": [{"decision": "Decision 1", "rationale": "Rationale 1"}],
                    "learnings_extracted": [{"learning": "Learning 1", "pattern_type": "pattern"}],
                    "outcome": "Success",
                    "metadata": {},
                }
            ],
        ]

        journey = await journey_logger.complete_journey(
            journey_id="test-123",
            outcome="Success",
            context_end="Feature completed successfully",
        )

        assert journey.journey_id == "test-123"
        assert journey.journey_type == "implementation"
        assert journey.coherence_at_start == 0.5
        assert journey.coherence_at_end == 0.6
        assert journey.hiho_stable is True
        assert journey.outcome == "Success"
        assert len(journey.decisions_made) == 1
        assert len(journey.learnings_extracted) == 1

        # Verify DB was called twice (UPDATE and SELECT)
        assert mock_surreal_client.query.call_count == 2

    @pytest.mark.asyncio
    async def test_get_recent_journeys_all(self, journey_logger, mock_surreal_client):
        """Test getting recent journeys (all types)."""
        mock_surreal_client.query.return_value = [
            {
                "journey_id": "test-1",
                "journey_type": "implementation",
                "started_at": datetime.now().isoformat(),
                "coherence_at_start": 0.5,
                "coherence_at_end": 0.6,
                "hiho_stable": True,
                "flume_state_end": [0.1] * 256,
                "decisions_made": [],
                "learnings_extracted": [],
                "outcome": "Success",
                "metadata": {},
            }
        ]

        journeys = await journey_logger.get_recent_journeys(limit=10)

        assert len(journeys) == 1
        assert journeys[0].journey_id == "test-1"

        # Verify DB query
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "SELECT * FROM platform_journeys" in call_args[0][0]
        assert "ORDER BY started_at DESC" in call_args[0][0]
        assert call_args[0][1]["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_recent_journeys_filtered(self, journey_logger, mock_surreal_client):
        """Test getting recent journeys (filtered by type)."""
        mock_surreal_client.query.return_value = [
            {
                "journey_id": "test-1",
                "journey_type": "implementation",
                "started_at": datetime.now().isoformat(),
                "coherence_at_start": 0.5,
                "coherence_at_end": 0.6,
                "hiho_stable": True,
                "flume_state_end": [0.1] * 256,
                "decisions_made": [],
                "learnings_extracted": [],
                "outcome": "Success",
                "metadata": {},
            }
        ]

        journeys = await journey_logger.get_recent_journeys(journey_type="implementation", limit=5)

        assert len(journeys) == 1

        # Verify DB query includes type filter
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "WHERE journey_type = $journey_type" in call_args[0][0]
        assert call_args[0][1]["journey_type"] == "implementation"
        assert call_args[0][1]["limit"] == 5

    @pytest.mark.asyncio
    async def test_numpy_array_conversion(self, journey_logger, mock_surreal_client, mock_vae_encoder):
        """Test that numpy arrays are converted to lists for JSON serialization."""
        # VAE returns numpy array
        mock_vae_encoder.encode.return_value = np.array([0.1] * 256)

        await journey_logger.start_journey(journey_type="test", context="Test context")

        # Verify the flume_state in DB query is a list, not numpy array
        call_args = mock_surreal_client.query.call_args
        flume_state = call_args[0][1]["flume_state"]
        assert isinstance(flume_state, list)
        assert len(flume_state) == 256


class TestSingletonAccessor:
    """Test singleton accessor functions."""

    def test_get_journey_logger(self):
        """Test getting global journey logger."""
        reset_journey_logger()

        logger1 = get_journey_logger()
        logger2 = get_journey_logger()

        assert logger1 is logger2

    def test_reset_journey_logger(self):
        """Test resetting global journey logger."""
        logger1 = get_journey_logger()
        reset_journey_logger()
        logger2 = get_journey_logger()

        assert logger1 is not logger2
