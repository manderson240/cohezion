"""
Harness for hf_search_spaces tool.
Validates output schema via mocking.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch
from cohezion.mcp.servers.huggingface.server import hf_search_spaces

async def verify():
    print("Testing hf_search_spaces (Mocked)...")
    
    mock_spaces = [
        {"id": "s1", "author": "a1", "likes": 10},
        {"id": "s2", "author": "a2", "likes": 20}
    ]
    
    with patch("cohezion.mcp.servers.huggingface.server.get_service") as mock_get_service:
        service = MagicMock()
        service.search_spaces.return_value = asyncio.Future()
        service.search_spaces.return_value.set_result(mock_spaces)
        mock_get_service.return_value = service
        
        result = await hf_search_spaces("query")
        
        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["count"] == 2, "Count mismatch"
        assert len(result["spaces"]) == 2, "Spaces count mismatch"
        
    print("✅ hf_search_spaces harness passed.")
    return True

if __name__ == "__main__":
    asyncio.run(verify())
