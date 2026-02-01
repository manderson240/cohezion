"""
Verification for Gateway 9 (External Integration).
Tests EmailListenerAgent logic with mocks.
"""

import asyncio
import logging
import os
from unittest.mock import MagicMock, patch

from cohezion.swarm.agents.email_listener_agent import EmailListenerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)


async def test_email_listener():
    print("--- Testing EmailListenerAgent (Mocked) ---")

    # Mock NotificationConfig to bypass env check
    with patch(
        "cohezion.swarm.agents.email_listener_agent.NotificationConfig"
    ) as MockConfig:
        config_inst = MockConfig.from_env.return_value
        config_inst.sender_email = "bot@cohezion.ai"
        config_inst.sender_password = os.getenv("TEST_EMAIL_PASSWORD", "dummy")
        config_inst.recipient_email = "manderson240@gmail.com"

        agent = EmailListenerAgent()

        # Mock MailBox
        with patch("cohezion.swarm.agents.email_listener_agent.MailBox") as MockMailBox:
            # Setup mock mailbox context manager
            mailbox_inst = MockMailBox.return_value
            mailbox_inst.login.return_value.__enter__.return_value = mailbox_inst

            # Setup mock messages
            msg1 = MagicMock()
            msg1.subject = "Cohezion Prompt: Build a spaceship"
            msg1.from_ = "manderson240@gmail.com"  # Authorized
            msg1.text = "Body text"

            # Mock fetch return
            mailbox_inst.fetch.return_value = [msg1]

            # Run Process
            print("Processing mock inbox...")
            tasks = await agent.process()

            print(f"Tasks Found: {len(tasks)}")

            if len(tasks) == 1:
                print("✅ SUCCESS: Found authorized email.")
                print(f"Task: {tasks[0]}")
            else:
                print(f"❌ FAILURE: Expected 1 task, got {len(tasks)}")


if __name__ == "__main__":
    asyncio.run(test_email_listener())
