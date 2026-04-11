"""
Harness for github_create_issue_comment tool.
Validates output schema via mocking.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch
from cohezion.mcp.servers.github.server import github_create_issue_comment

async def verify():
    print("Testing github_create_issue_comment (Mocked)...")
    
    mock_comment = {
        "id": 456,
        "url": "https://github.com/manderson240/cohezion/issues/123#issuecomment-456",
        "created_at": "2026-04-11T00:00:00Z"
    }
    
    with patch("cohezion.mcp.servers.github.server.get_service") as mock_get_service:
        service = MagicMock()
        service.create_issue_comment.return_value = asyncio.Future()
        service.create_issue_comment.return_value.set_result(mock_comment)
        mock_get_service.return_value = service
        
        result = await github_create_issue_comment("manderson240", "cohezion", 123, "Test Comment")
        
        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["id"] == 456, "ID mismatch"
        assert "url" in result, "Missing url"
        
    print("✅ github_create_issue_comment harness passed.")
    return True

if __name__ == "__main__":
    asyncio.run(verify())
