"""
Verification for Gateway 9 Expansion (Inbox Miner).
Tests InboxMiner classification logic with mocks.
"""

import asyncio
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from cohezion.swarm.agents.inbox_miner import InboxMiner

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_inbox_miner():
    print("--- Testing InboxMiner (Mocked) ---")
    
    # Mock NotificationConfig
    with patch("cohezion.swarm.agents.email_listener_agent.NotificationConfig") as MockConfig:
        config_inst = MockConfig.from_env.return_value
        config_inst.sender_email = "bot@cohezion.ai"
        config_inst.sender_password = "dummy"
        
        agent = InboxMiner()
        
        # Mock _call_ollama to return canned responses based on prompt
        async def mock_llm(prompt, **kwargs):
            if "Bug fix" in prompt or "Optimize" in prompt:
                return "RANK: 1\nTASK: Fix database bug"
            else:
                return "RANK: 0\nTASK: Ignore"
        
        agent._call_ollama = AsyncMock(side_effect=mock_llm)
        
        # Mock MailBox
        with patch("cohezion.swarm.agents.inbox_miner.MailBox") as MockMailBox:
            mailbox_inst = MockMailBox.return_value
            mailbox_inst.login.return_value.__enter__.return_value = mailbox_inst
            
            # Msg 1: Relevant
            msg1 = MagicMock()
            msg1.subject = "Urgent: Optimize SurrealDB queries"
            msg1.text = "We need to fix the slow queries in TimeKeeper."
            msg1.from_ = "manderson240@gmail.com"
            msg1.date = "2026-01-18"
            
            # Msg 2: Irrelevant
            msg2 = MagicMock()
            msg2.subject = "Dinner tonight?"
            msg2.text = "Pizza or tacos?"
            msg2.from_ = "manderson240@gmail.com"
            msg2.date = "2026-01-18"
            
            # Mock fetch
            mailbox_inst.fetch.return_value = [msg1, msg2]
            
            # Run Mine History
            print("Mining last 2 emails...")
            tasks = await agent.mine_history(limit=2)
            
            print(f"Tasks Found (Rank 1): {len(tasks)}")
            
            if len(tasks) == 1 and tasks[0]["task_title"] == "Fix database bug":
                print("✅ SUCCESS: Correctly classified relevant vs irrelevant.")
                print(f"Mined Task: {tasks[0]}")
            else:
                print(f"❌ FAILURE: Expected 1 task, got {len(tasks)}")

if __name__ == "__main__":
    asyncio.run(test_inbox_miner())
