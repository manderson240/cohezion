"""
Harness for github_create_issue tool.
Validates output schema via mocking.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.servers.github.server import github_create_issue


async def verify():
    print("Testing github_create_issue (Mocked)...")

    mock_issue = {
        "number": 123,
        "title": "Test Issue",
        "state": "open",
        "url": "https://github.com/manderson240/cohezion/issues/123",
    }

    with patch("cohezion.mcp.servers.github.server.get_service") as mock_get_service:
        service = MagicMock()
        service.create_issue.return_value = asyncio.Future()
        service.create_issue.return_value.set_result(mock_issue)
        mock_get_service.return_value = service

        result = await github_create_issue("manderson240", "cohezion", "Test Issue", "Body")

        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["number"] == 123, "Number mismatch"
        assert result["title"] == "Test Issue", "Title mismatch"

    print("✅ github_create_issue harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
