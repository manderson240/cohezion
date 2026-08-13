import pytest
import urllib.error
from unittest.mock import AsyncMock, MagicMock, patch
from cohezion.researcher.lanes.verify_evolve import VerifyEvolveLane
from cohezion.mycelium.registry import MyceliumRegistry, MyceliumCluster

@pytest.mark.asyncio
async def test_query_mycelium_patterns_integration():
    """Verify verify_evolve lane queries the live MyceliumRegistry singleton."""
    MyceliumRegistry.reset_instance()
    registry = MyceliumRegistry.get_instance()
    
    # Add a mock cluster that should match
    cluster = MyceliumCluster(
        cluster_id="mycelium-0",
        centroid_twelve_d={},
        centroid_fabric={},
        member_event_ids=["evt-1"],
        member_agent_ids=set(),
        member_universe_ids={"univ-1"}
    )
    cluster.member_families = {"qwen3"}
    cluster.member_tasks = {"code"}
    cluster.mean_coherence = 0.9
    registry.clusters.append(cluster)
    
    researcher = MagicMock()
    lane = VerifyEvolveLane(researcher)
    
    # Query qwen3-coder:30b (which resolves to family "qwen3") and task "code"
    results = await lane._query_mycelium_patterns("qwen3-coder:30b", "code")
    assert len(results) == 1
    assert results[0]["cluster_id"] == "mycelium-0"
    assert results[0]["size"] == 1

@pytest.mark.asyncio
async def test_query_ouroboros_healing_events_sanitization():
    """Verify that _query_ouroboros_healing_events raises ValueError on SQL injection inputs."""
    researcher = MagicMock()
    lane = VerifyEvolveLane(researcher)
    
    # Malformed inputs containing SQL injection syntax
    injection_inputs = [
        "model_id'; DROP TABLE precipitation_event; --",
        "model_id' OR '1'='1",
        "model_id\" OR \"1\"=\"1",
        "model_id; SELECT * FROM precipitation_event"
    ]
    
    for bad_id in injection_inputs:
        with pytest.raises(ValueError, match="Invalid model_id"):
            await lane._query_ouroboros_healing_events(bad_id)

@pytest.mark.asyncio
async def test_query_ouroboros_healing_events_db_success():
    """Verify that _query_ouroboros_healing_events builds the correct query and requests headers."""
    researcher = MagicMock()
    lane = VerifyEvolveLane(researcher)
    
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = b'[{"result":[{"model_id":"qwen3-coder:30b","kind":"HEALING_EVENT"}]}]'
    
    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        results = await lane._query_ouroboros_healing_events("qwen3-coder:30b")
        assert len(results) == 1
        assert results[0]["model_id"] == "qwen3-coder:30b"
        
        # Verify headers and body
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Surreal-ns") == "cohezion"
        assert req.get_header("Surreal-db") == "main"
        
        import json
        body = json.loads(req.data.decode())
        assert "HEALING_EVENT" in body["query"]
        assert "qwen3-coder:30b" in body["query"]

@pytest.mark.asyncio
async def test_query_ouroboros_healing_events_retry_logic():
    """Verify that _query_ouroboros_healing_events retries up to 3 times on connection failure."""
    researcher = MagicMock()
    lane = VerifyEvolveLane(researcher)
    
    # Simulate urllib raising HTTP/URL errors 2 times, then succeeding
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = b'[{"result":[]}]'
    
    call_count = 0
    def mock_urlopen_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise urllib.error.URLError("Connection refused")
        return mock_response
        
    with (
        patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect) as mock_urlopen,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep
    ):
        results = await lane._query_ouroboros_healing_events("qwen3-coder:30b")
        assert results == []
        assert call_count == 3
        assert mock_sleep.call_count == 2
