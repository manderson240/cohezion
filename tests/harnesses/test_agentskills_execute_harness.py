"""
Harness for agentskills_execute tool.
Validates output schema and governance logic.
"""

import asyncio
from unittest.mock import MagicMock, patch

from cohezion.mcp.agentskills_bridge import agentskills_execute


async def verify():
    print("Testing agentskills_execute...")

    # 1. Test blocked (Low autonomy)
    with patch("cohezion.mcp.agentskills_bridge.AutonomyEngine") as mock_engine_cls:
        mock_engine = MagicMock()
        mock_engine.can_perform.return_value = False
        mock_engine_cls.return_value = mock_engine

        result = await agentskills_execute("low_agent", "bash", {})
        assert result["success"] == False, "Should be blocked"
        assert "Governance Violation" in result["error"]

    # 2. Test allowed (High autonomy)
    with patch("cohezion.mcp.agentskills_bridge.AutonomyEngine") as mock_engine_cls:
        mock_engine = MagicMock()
        mock_engine.can_perform.return_value = True
        mock_engine_cls.return_value = mock_engine

        result = await agentskills_execute("high_agent", "bash", {"command": "ls"})
        assert result["success"] == True, "Should be allowed"
        assert result["skill"] == "bash"

    print("✅ agentskills_execute harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
