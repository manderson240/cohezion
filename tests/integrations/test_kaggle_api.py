from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cohezion.integrations.kaggle_api import KaggleAPI
from cohezion.reliability import CircuitState, _circuits


@pytest.fixture(autouse=True)
def reset_circuits():
    """Reset all circuits before each test."""
    for circuit in _circuits.values():
        circuit.reset()
    yield

@pytest.mark.asyncio
async def test_kaggle_api_initialization():
    """Test that KaggleAPI initializes correctly with circuit breaker and pool."""
    api = KaggleAPI(username="testuser", key="testkey")
    assert api.username == "testuser"
    assert api.key == "testkey"
    assert api.circuit.name == "kaggle_api"
    assert api.pool.base_url == "https://www.kaggle.com/api/v1"

@pytest.mark.asyncio
async def test_download_dataset_success():
    """Test successful dataset download."""
    api = KaggleAPI(username="testuser", key="testkey")
    dataset_name = "nvidia/nvidia-nemotron-model-reasoning-challenge"
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b"fake dataset content"
    
    with patch.object(api.pool, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await api.download_dataset(dataset_name)
        
        assert result == b"fake dataset content"
        mock_get.assert_called_once_with(
            f"/datasets/download/{dataset_name}", 
            auth=("testuser", "testkey")
        )
        assert api.circuit.state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_download_dataset_failure_opens_circuit():
    """Test that repeated failures open the circuit breaker."""
    api = KaggleAPI(username="testuser", key="testkey", failure_threshold=2)
    dataset_name = "invalid/dataset"
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found", request=MagicMock(), response=mock_response
    )
    
    with patch.object(api.pool, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        # First failure
        with pytest.raises(httpx.HTTPStatusError):
            await api.download_dataset(dataset_name)
        assert api.circuit.state == CircuitState.CLOSED
        
        # Second failure - should open circuit
        with pytest.raises(httpx.HTTPStatusError):
            await api.download_dataset(dataset_name)
        assert api.circuit.state == CircuitState.OPEN

@pytest.mark.asyncio
async def test_push_notebook_success():
    """Test successful notebook push."""
    api = KaggleAPI(username="testuser", key="testkey")
    notebook_id = "test-notebook"
    code = "print('hello')"
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "url": "https://kaggle.com/test/test-notebook"}
    
    with patch.object(api.pool, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await api.push_notebook(notebook_id, code)
        
        assert result["status"] == "ok"
        mock_post.assert_called_once()
        assert api.circuit.state == CircuitState.CLOSED
