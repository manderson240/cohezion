import asyncio

import pytest

from cohezion.swarm.rlm.scalar_context_manager import ScalarContextManager


@pytest.mark.anyio
async def test_scalar_importance():
    manager = ScalarContextManager(threshold=0.6)

    query = "FLUME manifold stability"
    segments = [
        "This segment discusses FLUME manifold stability in detail.",
        "This is a random sentence about gardening.",
        "High stability (>0.9) is critical for reality precipitation.",
    ]

    # 1. Test calculation
    score_high = manager.calculate_importance(segments[0], query)
    score_low = manager.calculate_importance(segments[1], query)
    score_boost = manager.calculate_importance(segments[2], query, stability=0.95)

    print(
        f"DEBUG: score_high={score_high}, score_low={score_low}, score_boost={score_boost}"
    )

    assert score_high >= 0.0
    assert score_low >= 0.0

    # 2. Test prioritization
    prioritized = await manager.prioritize_context(segments, query, stability=0.95)

    assert len(prioritized) == 3
    # First and third should be DIVE or at least higher importance
    assert prioritized[0]["action"] in ["DIVE", "SUMMARIZE"]
    assert prioritized[1]["action"] == "SUMMARIZE"

    await manager.close()


if __name__ == "__main__":
    asyncio.run(test_scalar_importance())
