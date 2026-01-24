
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
from cohezion.swarm.agents.handoff_agent import HandoffAgent

@pytest.mark.anyio
async def test_handoff_generation():
    # Mock DB to avoid external hits
    with patch("cohezion.db.surreal_client.SurrealClient.connect", new_callable=AsyncMock), \
         patch("cohezion.db.surreal_client.SurrealClient.store_node", new_callable=AsyncMock), \
         patch("cohezion.db.surreal_client.SurrealClient.close", new_callable=AsyncMock):

        agent = HandoffAgent()

        session_data = {
            "query": "Test Session",
            "expert_responses": {"architect": "Built a bridge."},
            "synthesis": "Everything is fine.",
            "confidence": 0.85,
            "created_at": "2026-01-21T07:16:42Z"
        }

        # Mock _call_ollama to avoid LLM trip
        agent._call_ollama = AsyncMock(return_value="SNAPHOT_SUMMARY_PLACEHOLDER")

        snapshot = await agent.create_snapshot(session_data)

        assert "SNAPHOT_SUMMARY_PLACEHOLDER" in snapshot
        await agent.close()

if __name__ == "__main__":
    asyncio.run(test_handoff_generation())
