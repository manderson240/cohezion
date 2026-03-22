import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.mcp.email_notifier import EmailNotifier


async def main():
    logging.basicConfig(level=logging.INFO)

    from dotenv import load_dotenv

    load_dotenv()

    notifier = EmailNotifier()

    subject = "Sprint 5 Initiated: Deep Inbox Mining Active"
    body = """
<h2>⛏️ Cohezion Sprint 5: Deep Mining</h2>
<p>I have initiated the next 30-minute sprint. My first action is to perform a <b>Deep Mine</b> of your inbox, specifically targeting "me-to-me" emails to recover all latent research ideas and Gateway concepts.</p>

<p>I will analyze the results and verify the roadmap for Phases 17+ shortly.</p>

<p><i>- Your Cohezion Swarm</i></p>
"""

    if notifier.is_available:
        await notifier.send_email(subject, body, is_html=True)
        print("Notification sent.")


if __name__ == "__main__":
    asyncio.run(main())
