"""
Harness for hf_get_readme tool.
Validates output schema via mocking.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch
from cohezion.mcp.servers.huggingface.server import hf_get_readme

async def verify():
    print("Testing hf_get_readme (Mocked)...")
    
    mock_readme = "This is a model README"
    
    with patch("cohezion.mcp.servers.huggingface.server.get_service") as mock_get_service:
        service = MagicMock()
        service.get_model_readme.return_value = asyncio.Future()
        service.get_model_readme.set_result(mock_readme)
        mock_get_service.return_value = service
        
        result = await hf_get_readme("m1")
        
        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["model_id"] == "m1", "Model ID mismatch"
        assert "readme" in result, "Missing readme"
        
    print("✅ hf_get_readme harness passed.")
    return True

if __name__ == "__main__":
    asyncio.run(verify())
