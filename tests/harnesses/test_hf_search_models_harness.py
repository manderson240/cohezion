"""
Harness for hf_search_models tool.
Validates output schema via mocking.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch
from cohezion.mcp.servers.huggingface.server import hf_search_models

async def verify():
    print("Testing hf_search_models (Mocked)...")
    
    mock_models = [
        {"id": "m1", "modelId": "m1", "downloads": 10},
        {"id": "m2", "modelId": "m2", "downloads": 20}
    ]
    
    with patch("cohezion.mcp.servers.huggingface.server.get_service") as mock_get_service:
        service = MagicMock()
        service.search_models.return_value = asyncio.Future()
        service.search_models.return_value.set_result(mock_models)
        mock_get_service.return_value = service
        
        result = await hf_search_models("query")
        
        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["count"] == 2, "Count mismatch"
        assert len(result["models"]) == 2, "Models count mismatch"
        
    print("✅ hf_search_models harness passed.")
    return True

if __name__ == "__main__":
    asyncio.run(verify())
