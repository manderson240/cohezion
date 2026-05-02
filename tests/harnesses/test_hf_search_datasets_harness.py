"""
Harness for hf_search_datasets tool.
Validates output schema via mocking.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.servers.huggingface.server import hf_search_datasets


async def verify():
    print("Testing hf_search_datasets (Mocked)...")

    mock_datasets = [
        {"id": "d1", "author": "a1", "downloads": 100},
        {"id": "d2", "author": "a2", "downloads": 200},
    ]

    with patch("cohezion.mcp.servers.huggingface.server.get_service") as mock_get_service:
        service = MagicMock()
        service.search_datasets.return_value = asyncio.Future()
        service.search_datasets.return_value.set_result(mock_datasets)
        mock_get_service.return_value = service

        result = await hf_search_datasets("query")

        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["count"] == 2, "Count mismatch"
        assert len(result["datasets"]) == 2, "Datasets count mismatch"

    print("✅ hf_search_datasets harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
