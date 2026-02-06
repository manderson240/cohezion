"""
ASCENDED COHEZION - Email Notification System
Milestone Alerts and Daily Digest

Manages email notifications for autonomous universe missions.
Uses Python's smtplib for email delivery.

Email: manderson240@gmail.com
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages email notifications for milestone alerts and daily digests.

    Uses SMTP for email delivery. Configuration is stored in
    ~/.config/cohezion/email_config.json
    """

    def __init__(self, recipient_email: str = "manderson240@gmail.com"):
        self.recipient = recipient_email
        self.config_path = Path.home() / ".config" / "cohezion" / "email_config.json"
        self.sent_emails: list[dict[str, Any]] = []

        # Default SMTP settings (user can override in config)
        self.smtp_config = self._load_config()

        logger.info("📧 NotificationManager initialized")
        logger.info(f"   Recipient: {recipient_email}")
        logger.info(f"   SMTP: {self.smtp_config.get('smtp_server', 'not configured')}")

    def _load_config(self) -> dict[str, Any]:
        """Load SMTP configuration from file"""
        default_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "",
            "smtp_password": "",
            "sender_email": "",
            "enabled": False,
            "digest_time": "16:00",  # 4 PM daily
        }

        try:
            if self.config_path.exists():
                config = json.loads(self.config_path.read_text())
                default_config.update(config)
        except Exception as e:
            logger.warning(f"Could not load email config: {e}")

        return default_config

    def save_config(self, config: dict[str, Any]):
        """Save SMTP configuration"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, indent=2))
        self.smtp_config = config

    async def send_milestone(
        self,
        mission_id: str,
        milestone: str,
        message: str,
        details: dict | None = None,
    ) -> bool:
        """Send immediate milestone notification"""

        if not self.smtp_config.get("enabled", False):
            logger.info(f"[Email would send] Milestone: {milestone} - {message}")
            return False

        try:
            subject = f"🌌 ASCENDED COHEZION - {milestone.replace('_', ' ').title()}"

            body = f"""
ASCENDED COHEZION Universe Simulation Alert

Mission: {mission_id}
Milestone: {milestone}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{message}

"""

            if details:
                body += "Details:\n"
                for key, value in details.items():
                    body += f"  {key}: {value}\n"

            body += """
---
ASCENDED COHEZION - Autonomous Universe Simulation
System Status: OPERATIONAL
Next Milestone: Check dashboard for updates
"""

            await self._send_email(subject, body)

            # Log sent email
            self.sent_emails.append(
                {
                    "type": "milestone",
                    "mission_id": mission_id,
                    "milestone": milestone,
                    "timestamp": datetime.now().isoformat(),
                    "message": message,
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send milestone email: {e}")
            return False

    async def send_daily_digest(
        self,
        date: str,
        all_tracks_data: list[dict[str, Any]],
        system_metrics: dict | None = None,
    ) -> bool:
        """Send comprehensive daily digest"""

        if not self.smtp_config.get("enabled", False):
            logger.info("[Email would send] Daily digest")
            return False

        try:
            subject = f"📊 ASCENDED COHEZION Daily Report - {date}"

            body = f"""
ASCENDED COHEZION - Daily Universe Report
Date: {date}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

═══════════════════════════════════════════════
TRACK SUMMARY
═══════════════════════════════════════════════
"""

            for track_data in all_tracks_data:
                track_name = track_data.get("track_type", "unknown")
                runs = track_data.get("runs_completed", 0)
                avg_grade = track_data.get("avg_grade", "N/A")
                avg_hiho = track_data.get("avg_hiho_time", "N/A")

                body += f"""
{track_name.upper()}
  Runs Completed: {runs}
  Average Grade: {avg_grade}
  Avg HIHO Convergence: {avg_hiho}
  Status: {track_data.get("status", "unknown")}
"""

            # Cloud feedback applied
            body += """
═══════════════════════════════════════════════
IMPROVEMENTS APPLIED
═══════════════════════════════════════════════
"""

            # System metrics
            if system_metrics:
                body += """
═══════════════════════════════════════════════
SYSTEM METRICS
═══════════════════════════════════════════════
"""
                for key, value in system_metrics.items():
                    body += f"  {key}: {value}\n"

            # Upcoming schedule
            body += """
═══════════════════════════════════════════════
UPCOMING SCHEDULE
═══════════════════════════════════════════════

Track A (Rapid):     06:00, 12:00, 18:00 (4h runs)
Track B (Balanced):  04:00, 16:00 (12h runs)
Track C (Deep):      00:00 daily (24h runs)

═══════════════════════════════════════════════
"""

            body += """
Dashboard: http://localhost:8000/universe-dashboard
System: OPERATIONAL | HIHO: STABLE | Compound Engineering: ACTIVE

---
ASCENDED COHEZION
Autonomous Universe Simulation with Cloud Grading
"""

            await self._send_email(subject, body)

            self.sent_emails.append(
                {
                    "type": "digest",
                    "date": date,
                    "timestamp": datetime.now().isoformat(),
                    "tracks": len(all_tracks_data),
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send daily digest: {e}")
            return False

    async def _send_email(self, subject: str, body: str) -> bool:
        """Send email via SMTP"""

        if not all(
            [
                self.smtp_config.get("smtp_server"),
                self.smtp_config.get("smtp_username"),
                self.smtp_config.get("smtp_password"),
                self.smtp_config.get("sender_email"),
            ]
        ):
            logger.warning("SMTP not fully configured, email not sent")
            logger.info(f"[Would send] Subject: {subject}")
            return False

        # Create message
        msg = MIMEMultipart()
        msg["From"] = self.smtp_config["sender_email"]
        msg["To"] = self.recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # Send via SMTP
        try:
            server = smtplib.SMTP(
                self.smtp_config["smtp_server"], self.smtp_config["smtp_port"]
            )
            server.starttls()
            server.login(
                self.smtp_config["smtp_username"], self.smtp_config["smtp_password"]
            )

            server.send_message(msg)
            server.quit()

            logger.info(f"📧 Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False

    def get_notification_history(self, limit: int = 50) -> list[dict]:
        """Get history of sent notifications"""
        return self.sent_emails[-limit:]

    def setup_gmail(self, username: str, app_password: str):
        """Helper to setup Gmail SMTP"""
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": username,
            "smtp_password": app_password,
            "sender_email": username,
            "enabled": True,
            "digest_time": "16:00",
        }
        self.save_config(config)
        logger.info("Gmail SMTP configured")


# Example usage
if __name__ == "__main__":
    import json

    # Create notification manager
    notifier = NotificationManager("manderson240@gmail.com")

    # Example: Send test milestone
    asyncio.run(
        notifier.send_milestone(
            mission_id="test_001",
            milestone="mission_start",
            message="Test mission started successfully",
            details={"universes": 6, "duration": "4h"},
        )
    )
