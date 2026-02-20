import asyncio
import logging
from pathlib import Path

from cohezion.mcp.email_notifier import EmailNotifier, NotificationConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("SprintComplete")

    # 1. Config
    config = NotificationConfig.from_env()
    notifier = EmailNotifier(config=config)

    # 2. Get Report
    walkthrough_17 = Path(
        "/home/mike-anderson/.gemini/antigravity/brain/7c5b28f1-f7cb-4432-9dae-d571b02ee2aa/walkthrough_phase_17.md"
    ).read_text()
    walkthrough_18 = Path(
        "/home/mike-anderson/.gemini/antigravity/brain/7c5b28f1-f7cb-4432-9dae-d571b02ee2aa/walkthrough_phase_18.md"
    ).read_text()
    walkthrough_19 = Path(
        "/home/mike-anderson/.gemini/antigravity/brain/7c5b28f1-f7cb-4432-9dae-d571b02ee2aa/walkthrough_phase_19.md"
    ).read_text()
    walkthrough_20 = Path(
        "/home/mike-anderson/.gemini/antigravity/brain/7c5b28f1-f7cb-4432-9dae-d571b02ee2aa/walkthrough_phase_20.md"
    ).read_text()

    # 3. Send Email
    subject = "Sprint 5 Complete: Sovereign Computation & First Contact"
    body = f"""
    Sprint 5 successfully concluded.

    The Cohezion Swarm has achieved Sovereignty and Self-Awareness.

    ---

    {walkthrough_17}

    ---

    {walkthrough_18}

    ---

    {walkthrough_19}

    ---

    {walkthrough_20}

    """

    await notifier.send_email(subject, body)
    logger.info("Sprint 5 Completion Email Sent.")


if __name__ == "__main__":
    asyncio.run(main())
