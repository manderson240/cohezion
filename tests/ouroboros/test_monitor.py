from unittest.mock import AsyncMock, patch

import pytest

from cohezion.ouroboros.monitor import OuroborosMonitor


@pytest.mark.asyncio
async def test_monitor_initialization():
    """Test that OuroborosMonitor initializes with correct config."""
    monitor = OuroborosMonitor(
        url="ws://localhost:8000/rpc",
        namespace="test_ns",
        database="test_db"
    )
    assert monitor.url == "ws://localhost:8000/rpc"
    assert monitor.namespace == "test_ns"
    assert monitor.database == "test_db"

@pytest.mark.asyncio
async def test_fetch_recent_trajectories_success():
    """Test that fetch_recent_trajectories queries SurrealDB correctly."""
    mock_db = AsyncMock()
    mock_db.query.return_value = [{"result": [{"id": "traj:1", "coherence": 0.45}, {"id": "traj:2", "coherence": 0.55}]}]
    
    with patch("cohezion.ouroboros.monitor.AsyncSurreal") as mock_surreal_class:
        mock_surreal_instance = mock_surreal_class.return_value
        mock_surreal_instance.__aenter__ = AsyncMock(return_value=mock_db)
        mock_surreal_instance.__aexit__ = AsyncMock(return_value=None)
        
        monitor = OuroborosMonitor()
        trajectories = await monitor.fetch_recent_trajectories(limit=10)
        
        assert len(trajectories) == 2
        assert trajectories[0]["coherence"] == 0.45
        mock_db.query.assert_called_once()
        query_str = mock_db.query.call_args[0][0]
        assert "SELECT * FROM trajectory" in query_str
        assert "LIMIT 10" in query_str

@pytest.mark.asyncio
async def test_fetch_recent_trajectories_failure():
    """Test handling of database query failure."""
    mock_db = AsyncMock()
    mock_db.query.side_effect = Exception("Surreal Query Error")
    
    with patch("cohezion.ouroboros.monitor.AsyncSurreal") as mock_surreal_class:
        mock_surreal_instance = mock_surreal_class.return_value
        mock_surreal_instance.__aenter__ = AsyncMock(return_value=mock_db)
        mock_surreal_instance.__aexit__ = AsyncMock(return_value=None)
        
        monitor = OuroborosMonitor()
        with pytest.raises(Exception, match="Surreal Query Error"):
            await monitor.fetch_recent_trajectories()
