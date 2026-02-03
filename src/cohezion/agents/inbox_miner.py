"""
Inbox Miner (Gateway 9 Expansion).

Mines historical emails for potential Cohezion tasks.
Classifies them as 1 (Relevant) or 0 (Irrelevant).
"""

import asyncio
import logging
from typing import Any

from imap_tools import MailBox

from cohezion.core.time_keeper import get_time_keeper
from cohezion.agents.email_listener_agent import EmailListenerAgent

logger = logging.getLogger(__name__)


class InboxMiner(EmailListenerAgent):
    """
    Miner agent that scans historical emails and classifies them.
    Inherits auth and base logic from EmailListenerAgent.
    """

    SYSTEM_PROMPT = """You are a Cohezion Task Miner.
Your job is to analyze an email and determine if it contains a task relevant to improving the Cohezion platform.

Output exactly two lines:
RANK: [1 or 0] (1 = Cohezion Improvement Task, 0 = Irrelevant/Personal/Spam)
TASK: [Short actionable title if Rank 1, else "Ignore"]

Criteria for Rank 1:
- Bug reports or feature requests for Cohezion
- Tech stack discussions (Python, AI, LLM, SurrealDB)
- Architecture ideas (Gateways, Agents, Swarm)

Criteria for Rank 0:
- Personal coordination (dinner, meetings)
- Marketing/Spam
- Unrelated work
"""

    async def mine_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Fetch last N emails and classify them.
        Returns list of Rank 1 tasks.
        """
        if not self.email_config.sender_password:
            logger.warning("No credentials.")
            return []

        tk = get_time_keeper()
        valid_tasks = []

        try:
            await tk.log_event(
                self.__class__.__name__, "MINING_START", {"limit": limit}
            )

            # 1. Fetch
            emails = await asyncio.to_thread(self._fetch_history, limit)
            logger.info(f"Fetched {len(emails)} historical emails.")

            # 2. Classify (Sequential to avoid rate limits, or parallel batches)
            for _i, email in enumerate(emails):
                rank, task_title = await self._classify_email(
                    email.subject, email.text or ""
                )

                if rank == 1:
                    task = {
                        "source": "email_history",
                        "sender": email.from_,
                        "original_subject": email.subject,
                        "task_title": task_title,
                        "timestamp": str(email.date),
                        "rank": 1,
                    }
                    valid_tasks.append(task)
                    logger.info(f"Generated Task: {task_title}")

                    await tk.log_event(
                        self.__class__.__name__, "TASK_MINED", {"title": task_title}
                    )

            return valid_tasks

        except Exception as e:
            logger.error(f"Mining failed: {e}")
            await tk.log_event(
                self.__class__.__name__, "MINING_ERROR", {"error": str(e)}
            )
            return []

    def _fetch_history(self, limit: int) -> list[Any]:
        """Fetch last N emails from authorized sender (SEEN or UNSEEN)."""
        messages = []
        try:
            with MailBox(self.imap_host).login(
                self.email_config.sender_email, self.email_config.sender_password
            ) as mailbox:
                # Fetch recent N messages from sender, reversed (newest first)
                criteria = f'FROM "{self.authorized_sender}"'
                for msg in mailbox.fetch(criteria, limit=limit, reverse=True):
                    messages.append(msg)

        except Exception as e:
            logger.error(f"IMAP Fetch Error: {e}")
            raise
        return messages

    async def _classify_email(self, subject: str, body: str) -> tuple[int, str]:
        """
        Use LLM to classify email.
        Returns (rank, task_title).
        """
        # Truncate body to save tokens
        clean_body = body[:2000].replace("\n", " ")
        prompt = f"Subject: {subject}\nBody: {clean_body}\n\nClassify this email."

        try:
            response = await self._call_ollama(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.0,  # Deterministic
                max_tokens=50,
            )

            # Parse response
            lines = response.strip().split("\n")
            rank = 0
            title = "Ignore"

            for line in lines:
                if line.startswith("RANK:"):
                    try:
                        rank = int(line.split(":")[1].strip())
                    except:
                        pass
                elif line.startswith("TASK:"):
                    title = line.split(":", 1)[1].strip()

            return rank, title

        except Exception as e:
            logger.warning(f"Classification failed: {e}")
            return 0, "Error"


# --- Test / Demo ---
if __name__ == "__main__":
    asyncio.run(InboxMiner().mine_history(limit=5))
