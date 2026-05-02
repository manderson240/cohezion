"""
Harness for github_list_issues tool.
Validates output schema via mocking.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.servers.github.server import github_list_issues


async def verify():
    print("Testing github_list_issues (Mocked)...")

    mock_issues = [
        {
            "number": 1,
            "title": "Issue 1",
            "state": "open",
            "url": "url1",
            "created_at": "ts1",
            "labels": [],
        },
        {
            "number": 2,
            "title": "Issue 2",
            "state": "open",
            "url": "url2",
            "created_at": "ts2",
            "labels": ["bug"],
        },
    ]

    with patch("cohezion.mcp.servers.github.server.get_service") as mock_get_service:
        service = MagicMock()
        service.list_issues.return_value = asyncio.Future()
        service.list_issues.return_value.set_result(mock_issues)
        mock_get_service.return_value = service

        result = await github_list_issues("owner", "repo")

        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert "issues" in result, "Missing issues key"
        assert len(result["issues"]) == 2, "Issues count mismatch"

    print("✅ github_list_issues harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
