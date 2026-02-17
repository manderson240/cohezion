import asyncio
import logging
import sys
from pathlib import Path

from imap_tools import A, MailBox


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.mcp.email_notifier import NotificationConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DeepMiner")

    config = NotificationConfig.from_env()
    sender = config.recipient_email or "manderson240@gmail.com"
    password = config.sender_password

    if not password:
        logger.error("No email password found in env.")
        return

    print(f"\n--- ⛏️ Deep Mining Inbox: {sender} -> {sender} ---")

    try:
        with MailBox("imap.gmail.com").login(sender, password) as mailbox:
            # Criteria: FROM user AND TO user (me-to-me)
            # Fetching last 100 emails to ensure we catch everything
            # Using A(from_=sender, to=sender) might be strict on some servers,
            # let's try raw criteria or just FROM and filter in loop.

            # Note: valid criteria for imap_tools is usually a single string or A object key-values
            # Gmail treats 'from' and 'to' reliably.

            criteria = A(from_=sender, to=sender)

            count = 0
            for msg in mailbox.fetch(criteria, limit=50, reverse=True):
                print(f"\n📧 [{msg.date.strftime('%Y-%m-%d')}] {msg.subject}")

                # Simple keyword heuristic to find relevant content
                body_lower = (msg.text or "").lower()
                keywords = [
                    "gateway",
                    "phase",
                    "cohezion",
                    "research",
                    "idea",
                    "sprint",
                ]

                if any(k in body_lower or k in msg.subject.lower() for k in keywords):
                    print("   MATCH: Found relevant keywords.")
                    # Print first 200 chars of body
                    print(f"   BODY: {(msg.text or '')[:300]}...")
                    count += 1
                else:
                    print("   (Skipping: No keywords)")

            print(f"\n--- Mining Complete. Found {count} potentially relevant emails. ---")

    except Exception as e:
        logger.error(f"Mining failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
