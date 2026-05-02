"""
Harness for get_reward_status tool.
Validates output schema and data types.
"""

import asyncio

from cohezion.mcp.servers.rewards.server import get_reward_status


async def verify():
    print("Testing get_reward_status...")
    result = await get_reward_status("test_agent")

    # Invariant Checks
    assert isinstance(result, dict), "Result must be a dictionary"
    assert "agent_id" in result, "Missing agent_id"
    assert result["agent_id"] == "test_agent", "Agent ID mismatch"
    assert "total_xp" in result, "Missing total_xp"
    assert isinstance(result["total_xp"], int), "XP must be an integer"
    assert "achievements" in result, "Missing achievements"
    assert isinstance(result["achievements"], list), "Achievements must be a list"

    print("✅ get_reward_status harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
