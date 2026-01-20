"""
Email Listener Agent (Gateway 9).

Listens for emails from the authorized user and converts them into tasks.
Reuses authentication from existing email_notifier.
"""

import asyncio
import logging
import os
from typing import Any, List

from imap_tools import MailBox, AND
from cohezion.swarm.agents.base import BaseAgent
from cohezion.mcp.email_notifier import NotificationConfig
from cohezion.core.time_keeper import get_time_keeper

logger = logging.getLogger(__name__)

class EmailListenerAgent(BaseAgent):
    """
    Agent that monitors an IMAP inbox for commands/prompts.
    """
    
    def __init__(self, model_name: str = "mistral-small"):
        super().__init__(model_name=model_name)
        self.config = NotificationConfig.from_env()
        self.authorized_sender = self.config.recipient_email or "manderson240@gmail.com"
        self.imap_host = "imap.gmail.com" # Default for Gmail
        
        # Verify config
        if not self.config.sender_email or not self.config.sender_password:
            logger.warning("Email credentials missing! EmailListenerAgent will not work.")
            
    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """
        Process inbox check.
        Returns a list of new tasks extracted from emails.
        """
        if not self.config.sender_password:
            return []
            
        tk = get_time_keeper()
        tasks = []
        
        try:
            # We use synchronous imap_tools in a thread to catch IDLE or Poll
            # logging event
            await tk.log_event(self.__class__.__name__, "IMAP_CHECK_START", {})
            
            new_emails = await asyncio.to_thread(self._fetch_emails)
            
            for email in new_emails:
                task = {
                    "source": "email",
                    "sender": email.from_,
                    "subject": email.subject,
                    "body": email.text or email.html,
                    "timestamp": str(email.date)
                }
                tasks.append(task)
                
                # Log finding
                await tk.log_event(
                    self.__class__.__name__, 
                    "EMAIL_RECEIVED", 
                    {"subject": email.subject, "sender": email.from_}
                )
                
            return tasks
            
        except Exception as e:
            logger.error(f"Email fetch failed: {e}")
            await tk.log_event(self.__class__.__name__, "IMAP_ERROR", {"error": str(e)})
            return []

    def _fetch_emails(self) -> List[Any]:
        """
        Synchronous IMAP fetching logic.
        Fetches UNSEEN messages from authorized sender.
        """
        messages = []
        try:
            with MailBox(self.imap_host).login(
                self.config.sender_email, 
                self.config.sender_password
            ) as mailbox:
                
                # Criteria: Unseen AND From authorized sender
                criteria = AND(seen=False, from_=self.authorized_sender)
                
                for msg in mailbox.fetch(criteria, mark_seen=True):
                    messages.append(msg)
                    logger.info(f"Received email command: {msg.subject}")
                    
        except Exception as e:
            logger.error(f"IMAP Connection Error: {e}")
            raise
            
        return messages

# --- Test / Simulation ---
async def demo_listener():
    print("--- Checking for Email Commands ---")
    agent = EmailListenerAgent()
    tasks = await agent.process()
    print(f"Found {len(tasks)} new commands.")
    for t in tasks:
        print(f"Task: {t['subject']}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo_listener())
