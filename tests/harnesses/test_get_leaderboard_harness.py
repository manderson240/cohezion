"""
Harness for get_leaderboard tool.
Validates output schema and data types.
"""

import asyncio

from cohezion.mcp.servers.rewards.server import get_leaderboard


async def verify():
    print("Testing get_leaderboard...")
    result = await get_leaderboard(2)

    # Invariant Checks
    assert isinstance(result, list), "Result must be a list"
    assert len(result) <= 2, "Result length exceeds limit"

    for entry in result:
        assert isinstance(entry, dict), "Entry must be a dictionary"
        assert "rank" in entry, "Missing rank"
        assert "agent" in entry, "Missing agent"
        assert "xp" in entry, "Missing xp"
        assert isinstance(entry["xp"], int), "XP must be an integer"

    print("✅ get_leaderboard harness passed.")
    return True


if __name__ == "__main__":
    asyncio.run(verify())
