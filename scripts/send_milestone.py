#!/usr/bin/env python3
"""
Milestone emailer using existing working email_notifier
"""

import asyncio
import sys


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.mcp.email_notifier import EmailNotifier


def send_milestone(milestone_name, details):
    """Send milestone notification email."""
    subject = f"🎯 Cohezion: {milestone_name}"
    body = f"""
Cohezion Implementation Sprint

MILESTONE: {milestone_name}

{details}

Timestamp: {__import__("datetime").datetime.now().isoformat()}
"""

    # Use async email notifier
    async def send():
        notifier = EmailNotifier()
        if notifier.is_available:
            return await notifier.send_email(subject, body, is_html=False)
        return False

    result = asyncio.run(send())

    if result:
        print(f"✅ Email sent: {milestone_name}")
    else:
        print("⚠️  Email not configured, check .env")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        send_milestone(sys.argv[1], sys.argv[2])
