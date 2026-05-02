"""
Harness for github_search_repos tool.
Validates output schema via mocking.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.servers.github.server import github_search_repos


async def verify():
    print("Testing github_search_repos (Mocked)...")

    mock_repos = [
        {"name": "repo1", "full_name": "owner/repo1", "stars": 10},
        {"name": "repo2", "full_name": "owner/repo2", "stars": 20},
    ]

    with patch("cohezion.mcp.servers.github.server.get_service") as mock_get_service:
        service = MagicMock()
        service.search_repos.return_value = asyncio.Future()
        service.search_repos.return_value.set_result(mock_repos)
        mock_get_service.return_value = service

        result = await github_search_repos("query")

        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["count"] == 2, "Count mismatch"
        assert len(result["repositories"]) == 2, "Repositories count mismatch"

    print("✅ github_search_repos harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
