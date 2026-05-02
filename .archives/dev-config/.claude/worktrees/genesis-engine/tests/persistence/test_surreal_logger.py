from unittest.mock import AsyncMock, patch

import pytest
import torch

from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger
from cohezion.universe.triune_manifold import TriuneState


@pytest.fixture
def triune_state():
    return TriuneState(doer=torch.randn(12), thinker=torch.randn(512), knower=torch.randn(2048))


@pytest.mark.asyncio
async def test_surreal_logger_initialization():
    """Test that the logger initializes with correct config."""
    logger = SurrealTrajectoryLogger(url="ws://localhost:8000/rpc", namespace="test_ns", database="test_db")
    assert logger.url == "ws://localhost:8000/rpc"
    assert logger.namespace == "test_ns"
    assert logger.database == "test_db"


@pytest.mark.asyncio
async def test_log_trajectory_success(triune_state):
    """Test that log_trajectory correctly formats and inserts data."""
    mock_db = AsyncMock()

    # Properly mock the AsyncSurreal context manager
    with patch("cohezion.persistence.surreal_logger.AsyncSurreal") as mock_surreal_class:
        mock_surreal_instance = mock_surreal_class.return_value
        mock_surreal_instance.__aenter__ = AsyncMock(return_value=mock_db)
        mock_surreal_instance.__aexit__ = AsyncMock(return_value=None)

        logger = SurrealTrajectoryLogger()

        await logger.log_trajectory(trajectory_id="test_traj_123", state=triune_state, coherence=0.5)

        # Verify create call
        mock_db.create.assert_called_once()
        args, _ = mock_db.create.call_args
        assert args[0] == "trajectory"

        data = args[1]
        assert data["trajectory_id"] == "test_traj_123"
        assert data["coherence"] == 0.5
        assert len(data["doer"]) == 12
        assert len(data["thinker"]) == 512
        assert len(data["knower"]) == 2048
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_log_trajectory_db_failure(triune_state):
    """Test handling of database connection/insertion failure."""
    mock_db = AsyncMock()
    mock_db.use.side_effect = Exception("DB Connection Error")

    with patch("cohezion.persistence.surreal_logger.AsyncSurreal") as mock_surreal_class:
        mock_surreal_instance = mock_surreal_class.return_value
        mock_surreal_instance.__aenter__ = AsyncMock(return_value=mock_db)
        mock_surreal_instance.__aexit__ = AsyncMock(return_value=None)

        logger = SurrealTrajectoryLogger()

        with pytest.raises(Exception, match="DB Connection Error"):
            await logger.log_trajectory(trajectory_id="test_traj_failure", state=triune_state, coherence=0.5)
