"""
Harness for github_get_user tool.
Validates output schema via mocking.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.servers.github.server import github_get_user


async def verify():
    print("Testing github_get_user (Mocked)...")

    mock_user = {
        "login": "manderson240",
        "name": "Mike Anderson",
        "bio": "AI Engineer",
        "public_repos": 50,
        "followers": 100,
        "following": 50,
        "url": "https://github.com/manderson240",
        "created_at": "2020-01-01T00:00:00Z",
    }

    with patch("cohezion.mcp.servers.github.server.get_service") as mock_get_service:
        service = MagicMock()
        service.get_user.return_value = asyncio.Future()
        service.get_user.return_value.set_result(mock_user)
        mock_get_service.return_value = service

        result = await github_get_user("manderson240")

        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["login"] == "manderson240", "Login mismatch"
        assert "public_repos" in result, "Missing public_repos"

    print("✅ github_get_user harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
