"""
Email Notification Service.

Sends completion notifications via email.
Uses SMTP or Gmail API.
"""

import asyncio
import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Auto-load .env file for credentials
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Fallback: manually load .env if dotenv not installed
    _env_path = Path(__file__).parents[3] / ".env"
    if _env_path.exists():
        with open(_env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Email notification configuration."""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""  # App password
    recipient_email: str = ""

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        return cls(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            sender_email=os.getenv("NOTIFICATION_EMAIL", ""),
            sender_password=os.getenv("NOTIFICATION_PASSWORD", ""),
            recipient_email=os.getenv("NOTIFICATION_RECIPIENT", ""),
        )


class EmailNotifier:
    """
    Sends email notifications on task completion.

    Setup:
    1. Enable 2FA on Google account
    2. Create app password: https://myaccount.google.com/apppasswords
    3. Set environment variables:
       - NOTIFICATION_EMAIL: your.email@gmail.com
       - NOTIFICATION_PASSWORD: your-app-password
       - NOTIFICATION_RECIPIENT: where to send notifications
    """

    def __init__(self, config: NotificationConfig | None = None):
        self.config = config or NotificationConfig.from_env()
        self._available = bool(
            self.config.sender_email
            and self.config.sender_password
            and self.config.recipient_email
        )

    async def send_block_alert(
        self,
        task_title: str,
        message: str,
    ) -> bool:
        """Send a block alert when user input is required (phone notification)."""
        if not self._available:
            return False

        subject = f"🚨 Cohezion Blocked: Action Required - {task_title}"
        body = f"""
<h2>⚠️ Swarm Blocked: {task_title}</h2>
<p>The Cohezion swarm is blocked and requires your input to proceed.</p>
<div style="background-color: #fff3cd; padding: 15px; border-left: 5px solid #ffc107;">
    <b>Message:</b><br>{message}
</div>
<p>Reply via phone with <b>[CMD] resume</b> or other commands to continue.</p>
"""
        return await self._send_email(subject, body)

    @property
    def is_available(self) -> bool:
        return self._available

    async def send_completion(
        self,
        task_title: str,
        summary: str,
        retrospective_path: Path | None = None,
    ) -> bool:
        """Send task completion notification."""
        if not self._available:
            logger.warning("Email notifications not configured")
            return False

        subject = f"✅ Cohezion Task Complete: {task_title}"

        body = f"""
Cohezion Task Completed
=======================

Task: {task_title}
Completed: {datetime.now(UTC).isoformat()}

Summary:
{summary}
"""

        if retrospective_path and retrospective_path.exists():
            body += f"""
Retrospective:
{retrospective_path.read_text()[:2000]}
"""

        return await self._send_email(subject, body)

    async def send_report(
        self,
        subject: str,
        report: str,
    ) -> bool:
        """Send a general report."""
        if not self._available:
            return False

        return await self._send_email(f"📊 Cohezion: {subject}", report, is_html=False)

    async def send_email(
        self,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: list[Path] | None = None,
    ) -> bool:
        """Send a generic email."""
        if not self._available:
            return False

        return await self._send_email(
            subject, body, is_html=is_html, attachments=attachments
        )

    async def _send_email(
        self,
        subject: str,
        body: str,
        is_html: bool = True,
        attachments: list[Path] | None = None,
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.sender_email
            msg["To"] = self.config.recipient_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "html" if is_html else "plain"))

            # Attach files
            from email.mime.application import MIMEApplication
            from email.mime.image import MIMEImage

            if attachments:
                for path in attachments:
                    if not path.exists():
                        logger.warning(f"Attachment not found: {path}")
                        continue

                    with open(path, "rb") as f:
                        data = f.read()

                    if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
                        part = MIMEImage(data, name=path.name)
                    else:
                        part = MIMEApplication(data, Name=path.name)

                    part["Content-Disposition"] = f'attachment; filename="{path.name}"'
                    msg.attach(part)

            # Run SMTP in thread pool
            def send():
                with smtplib.SMTP(
                    self.config.smtp_host, self.config.smtp_port
                ) as server:
                    server.starttls()
                    server.login(self.config.sender_email, self.config.sender_password)
                    server.send_message(msg)

            await asyncio.to_thread(send)
            logger.info(
                f"Email sent: {subject} ({len(attachments) if attachments else 0} attachments)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class LocalNotifier:
    """
    Fallback: Write notifications to local file.
    """

    def __init__(self, path: Path | None = None):
        self.path = path or Path(".cohezion/notifications.md")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def send_completion(
        self,
        task_title: str,
        summary: str,
        retrospective_path: Path | None = None,
    ) -> bool:
        """Write completion to local file."""
        notification = f"""
## Task Complete: {task_title}
**Time:** {datetime.now(UTC).isoformat()}

{summary}

---
"""

        mode = "a" if self.path.exists() else "w"
        with open(self.path, mode) as f:
            if mode == "w":
                f.write("# Cohezion Notifications\n\n")
            f.write(notification)

        logger.info(f"Notification saved to {self.path}")
        return True


async def notify_completion(
    task_title: str,
    summary: str,
    retrospective_path: Path | None = None,
) -> bool:
    """Send completion notification via best available method."""
    email = EmailNotifier()

    if email.is_available:
        return await email.send_completion(task_title, summary, retrospective_path)

    # Fallback to local
    local = LocalNotifier()
    return await local.send_completion(task_title, summary, retrospective_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test
    result = asyncio.run(
        notify_completion(
            "Test Task",
            "This is a test notification",
        )
    )
    print(f"Notification sent: {result}")
