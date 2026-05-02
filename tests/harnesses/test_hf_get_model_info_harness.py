"""
Harness for hf_get_model_info tool.
Validates output schema via mocking.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.servers.huggingface.server import hf_get_model_info


async def verify():
    print("Testing hf_get_model_info (Mocked)...")

    mock_info = {"id": "m1", "modelId": "m1", "author": "a1", "downloads": 10}

    with patch("cohezion.mcp.servers.huggingface.server.get_service") as mock_get_service:
        service = MagicMock()
        service.get_model_info.return_value = asyncio.Future()
        service.get_model_info.return_value.set_result(mock_info)
        mock_get_service.return_value = service

        result = await hf_get_model_info("m1")

        # Invariant Checks
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result["id"] == "m1", "ID mismatch"

    print("✅ hf_get_model_info harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
