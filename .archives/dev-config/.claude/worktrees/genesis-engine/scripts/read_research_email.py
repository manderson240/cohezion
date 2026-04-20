import asyncio
import logging
import sys
from pathlib import Path

from imap_tools import MailBox


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.mcp.email_notifier import NotificationConfig


async def main():
    logging.basicConfig(level=logging.INFO)

    from dotenv import load_dotenv

    load_dotenv()

    email_config = NotificationConfig.from_env()
    imap_host = "imap.gmail.com"
    authorized_sender = email_config.recipient_email or "manderson240@gmail.com"

    print("\n--- Reading Research Email Body ---")

    with MailBox(imap_host).login(
        email_config.sender_email, email_config.sender_password
    ) as mailbox:
        criteria = f'FROM "{authorized_sender}" SUBJECT "Research Update"'
        for msg in mailbox.fetch(criteria, reverse=True):
            print(f"Subject: {msg.subject}")
            print(f"Date: {msg.date}")
            print("\nBody:")
            print(msg.text or msg.html)
            print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
