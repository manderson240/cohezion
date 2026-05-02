"""
Harness for github_get_repo tool.
Validates output schema via mocking.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.servers.github.server import github_get_repo


async def verify():
    print("Testing github_get_repo (Mocked)...")

    # Mock data
    mock_repo = {
        "name": "cohezion",
        "full_name": "manderson240/cohezion",
        "stars": 100,
        "forks": 10,
        "open_issues": 5,
    }

    # Mock the service response
    with patch("cohezion.mcp.servers.github.server.get_service") as mock_get_service:
        service = MagicMock()
        service.get_repo.return_value = asyncio.Future()
        service.get_repo.return_value.set_result(mock_repo)
        mock_get_service.return_value = service

        result = await github_get_repo("manderson240", "cohezion")

        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["name"] == "cohezion", "Name mismatch"
        assert "stars" in result, "Missing stars"

    print("✅ github_get_repo harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
