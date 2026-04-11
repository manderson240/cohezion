"""
Harness for hf_inference tool.
Validates output schema via mocking.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch
from cohezion.mcp.servers.huggingface.server import hf_inference

async def verify():
    print("Testing hf_inference (Mocked)...")
    
    mock_result = {
        "model_id": "m1",
        "result": [{"label": "positive", "score": 0.9}],
        "status": "success"
    }
    
    with patch("cohezion.mcp.servers.huggingface.server.get_service") as mock_get_service:
        service = MagicMock()
        service.get_inference_api.return_value = asyncio.Future()
        service.get_inference_api.return_value.set_result(mock_result)
        mock_get_service.return_value = service
        
        result = await hf_inference("m1", "I love this!")
        
        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["status"] == "success", "Status mismatch"
        assert result["model_id"] == "m1", "Model ID mismatch"
        
    print("✅ hf_inference harness passed.")
    return True

if __name__ == "__main__":
    asyncio.run(verify())
