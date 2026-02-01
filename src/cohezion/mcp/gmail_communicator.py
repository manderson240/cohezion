"""
Gmail Communication MCP Server.

Bidirectional email communication:
- Send reports/notifications to user
- Read inbox for user replies
- Parse commands from email subjects/body
- Act autonomously on user instructions

Uses OAuth2 for personal Gmail accounts.
"""

import asyncio
import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",  # For marking as read
]

# Paths
COHEZION_DIR = Path.home() / ".cohezion"
TOKEN_PATH = COHEZION_DIR / "gmail_token.json"
CREDS_PATH = COHEZION_DIR / "google_oauth.json"
INBOX_CACHE = COHEZION_DIR / "gmail_inbox_cache.json"

# Auto-load .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    _env_path = Path(__file__).parents[3] / ".env"
    if _env_path.exists():
        with open(_env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)


@dataclass
class EmailMessage:
    """Parsed email message."""

    id: str
    thread_id: str
    subject: str
    sender: str
    body: str
    timestamp: datetime
    is_reply: bool = False
    commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "sender": self.sender,
            "body": self.body[:500],  # Truncate for storage
            "timestamp": self.timestamp.isoformat(),
            "is_reply": self.is_reply,
            "commands": self.commands,
        }


@dataclass
class Command:
    """Parsed command from email."""

    action: str  # approve, reject, implement, question, etc.
    target: str  # What to act on
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1=highest, 10=lowest
    raw_text: str = ""


class GmailService:
    """Gmail API wrapper with OAuth2."""

    def __init__(self):
        self.creds = None
        self.service = None
        self._initialized = False
        self.user_email = os.getenv("NOTIFICATION_RECIPIENT", "manderson240@gmail.com")

    async def initialize(self) -> bool:
        """Initialize Gmail API connection."""
        if self._initialized:
            return True

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            logger.error(
                "Google API libraries not installed. Run: uv add google-auth-oauthlib google-api-python-client"
            )
            return False

        # Check for existing token
        if TOKEN_PATH.exists():
            self.creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        # Refresh or get new token
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing Gmail token...")
                self.creds.refresh(Request())
            else:
                if not CREDS_PATH.exists():
                    logger.error(f"OAuth credentials not found at {CREDS_PATH}")
                    return False

                logger.info("Starting OAuth flow for Gmail...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDS_PATH), SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save token
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_PATH, "w") as f:
                f.write(self.creds.to_json())

        # Build service
        self.service = build("gmail", "v1", credentials=self.creds)
        self._initialized = True
        logger.info("Gmail API initialized successfully")
        return True

    async def send_email(
        self,
        subject: str,
        body: str,
        to: str | None = None,
        is_html: bool = False,
        thread_id: str | None = None,
    ) -> bool:
        """Send an email."""
        if not await self.initialize():
            return False

        to = to or self.user_email

        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        message.attach(MIMEText(body, "html" if is_html else "plain"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body_data = {"raw": raw}

        if thread_id:
            body_data["threadId"] = thread_id

        try:
            await asyncio.to_thread(
                self.service.users()
                .messages()
                .send(userId="me", body=body_data)
                .execute
            )
            logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def check_inbox(
        self,
        since_hours: int = 24,
        unread_only: bool = True,
    ) -> list[EmailMessage]:
        """Check inbox for new messages."""
        if not await self.initialize():
            return []

        # Build query
        query_parts = []
        if unread_only:
            query_parts.append("is:unread")

        # Look for replies to our emails or messages with commands
        query_parts.append("(from:me OR subject:cohezion OR subject:antigravity)")

        # Time filter
        since = datetime.now(UTC) - timedelta(hours=since_hours)
        query_parts.append(f"after:{since.strftime('%Y/%m/%d')}")

        query = " ".join(query_parts)

        try:
            results = await asyncio.to_thread(
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=20)
                .execute
            )

            messages = []
            for msg_ref in results.get("messages", []):
                msg = await self._get_message(msg_ref["id"])
                if msg:
                    messages.append(msg)

            return messages
        except Exception as e:
            logger.error(f"Failed to check inbox: {e}")
            return []

    async def _get_message(self, msg_id: str) -> EmailMessage | None:
        """Get full message details."""
        try:
            msg = await asyncio.to_thread(
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute
            )

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

            # Extract body
            body = ""
            if "parts" in msg["payload"]:
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = base64.urlsafe_b64decode(
                            part["body"].get("data", "")
                        ).decode("utf-8", errors="ignore")
                        break
            elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
                body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode(
                    "utf-8", errors="ignore"
                )

            # Parse timestamp
            timestamp = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, UTC)

            # Check if this is a reply to our email
            is_reply = (
                "Re:" in headers.get("Subject", "")
                and "cohezion" in headers.get("Subject", "").lower()
            )

            # Extract commands from body
            commands = self._extract_commands(body)

            return EmailMessage(
                id=msg_id,
                thread_id=msg["threadId"],
                subject=headers.get("Subject", ""),
                sender=headers.get("From", ""),
                body=body,
                timestamp=timestamp,
                is_reply=is_reply,
                commands=commands,
            )
        except Exception as e:
            logger.error(f"Failed to get message {msg_id}: {e}")
            return None

    def _extract_commands(self, body: str) -> list[str]:
        """Extract commands from email body."""
        commands = []

        # Look for explicit command patterns
        patterns = [
            r"\[APPROVE\]",
            r"\[REJECT\]",
            r"\[IMPLEMENT\]:\s*(.+)",
            r"\[PRIORITY\]:\s*(\d+)",
            r"\[DO\]:\s*(.+)",
            r"(?:^|\n)>\s*(.+)",  # Quoted instructions
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE | re.MULTILINE)
            commands.extend(
                matches
                if isinstance(matches[0] if matches else "", str)
                else [m[0] for m in matches]
            )

        return commands

    async def mark_as_read(self, msg_id: str) -> bool:
        """Mark a message as read."""
        if not await self.initialize():
            return False

        try:
            await asyncio.to_thread(
                self.service.users()
                .messages()
                .modify(userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]})
                .execute
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return False


class CommandParser:
    """Parse natural language commands from emails."""

    COMMAND_PATTERNS = {
        "approve": [
            r"(?:please\s+)?approve",
            r"looks\s+good",
            r"go\s+ahead",
            r"proceed",
            r"\byes\b",
            r"\bok\b",
            r"ship\s+it",
        ],
        "reject": [
            r"(?:please\s+)?reject",
            r"don't\s+(?:do|proceed)",
            r"stop",
            r"\bno\b",
            r"cancel",
        ],
        "implement": [
            r"implement\s+(.+)",
            r"build\s+(.+)",
            r"create\s+(.+)",
            r"add\s+(.+)",
        ],
        "prioritize": [
            r"prioritize\s+(.+)",
            r"focus\s+on\s+(.+)",
            r"start\s+with\s+(.+)",
        ],
        "delete": [
            r"delete\s+(.+)",
            r"remove\s+(.+)",
        ],
        "question": [
            r"\?$",
            r"what\s+(?:is|are|about)",
            r"how\s+(?:do|can|should)",
        ],
    }

    @classmethod
    def parse(cls, text: str) -> list[Command]:
        """Parse commands from text."""
        commands = []
        text_lower = text.lower()

        for action, patterns in cls.COMMAND_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    target = matches[0] if isinstance(matches[0], str) else ""
                    commands.append(
                        Command(
                            action=action,
                            target=target.strip() if target else "",
                            raw_text=text[:200],
                        )
                    )
                    break  # Only one command per action type

        return commands


class GmailCommunicator:
    """
    Main communication hub for agent-user interaction via Gmail.

    Features:
    - Send status reports
    - Read user replies
    - Parse commands from emails
    - Queue actions for autonomous execution
    - Track conversation threads
    """

    def __init__(self):
        self.gmail = GmailService()
        self.parser = CommandParser()
        self.action_queue: list[Command] = []
        self.processed_ids: set[str] = set()
        self._load_processed_ids()

    def _load_processed_ids(self):
        """Load previously processed message IDs."""
        if INBOX_CACHE.exists():
            try:
                with open(INBOX_CACHE) as f:
                    data = json.load(f)
                    self.processed_ids = set(data.get("processed_ids", []))
            except Exception:
                pass

    def _save_processed_ids(self):
        """Save processed message IDs."""
        COHEZION_DIR.mkdir(parents=True, exist_ok=True)
        with open(INBOX_CACHE, "w") as f:
            json.dump(
                {
                    "processed_ids": list(self.processed_ids)[-100],  # Keep last 100
                    "last_check": datetime.now(UTC).isoformat(),
                },
                f,
            )

    async def send_report(
        self,
        title: str,
        content: str,
        request_response: bool = False,
    ) -> bool:
        """Send a report to the user."""
        subject = f"📊 Cohezion: {title}"

        if request_response:
            content += """

---
**Reply Options:**
- Reply with "APPROVE" to proceed
- Reply with "REJECT" to cancel
- Reply with specific instructions
- Reply with questions

I'll check for your response and act accordingly.
"""

        return await self.gmail.send_email(subject, content)

    async def check_for_responses(self) -> list[Command]:
        """Check inbox for user responses and parse commands."""
        messages = await self.gmail.check_inbox(since_hours=24, unread_only=True)

        new_commands = []
        for msg in messages:
            if msg.id in self.processed_ids:
                continue

            # Skip our own sent messages
            if "manderson240@gmail.com" not in msg.sender.lower():
                # Parse commands from reply
                commands = self.parser.parse(msg.body)
                if commands:
                    new_commands.extend(commands)
                    logger.info(
                        f"Found {len(commands)} commands in email: {msg.subject}"
                    )

                # Mark as processed
                await self.gmail.mark_as_read(msg.id)

            self.processed_ids.add(msg.id)

        self._save_processed_ids()
        self.action_queue.extend(new_commands)

        return new_commands

    async def get_pending_actions(self) -> list[Command]:
        """Get all pending actions from queue."""
        return list(self.action_queue)

    def complete_action(self, command: Command):
        """Mark an action as completed."""
        if command in self.action_queue:
            self.action_queue.remove(command)

    async def poll_loop(
        self,
        interval_minutes: int = 5,
        callback=None,
    ):
        """
        Continuously poll for new emails and process commands.

        Args:
            interval_minutes: How often to check
            callback: Async function to call with new commands
        """
        logger.info(f"Starting email poll loop (every {interval_minutes} min)")

        while True:
            try:
                commands = await self.check_for_responses()
                if commands and callback:
                    await callback(commands)
            except Exception as e:
                logger.error(f"Poll error: {e}")

            await asyncio.sleep(interval_minutes * 60)


# Convenience functions
_communicator: GmailCommunicator | None = None


def get_communicator() -> GmailCommunicator:
    """Get or create the global communicator."""
    global _communicator
    if _communicator is None:
        _communicator = GmailCommunicator()
    return _communicator


async def send_report(title: str, content: str, request_response: bool = False) -> bool:
    """Send a report via Gmail."""
    return await get_communicator().send_report(title, content, request_response)


async def check_for_responses() -> list[Command]:
    """Check for user email responses."""
    return await get_communicator().check_for_responses()


async def setup_oauth():
    """Run OAuth setup for Gmail."""
    gmail = GmailService()

    if not CREDS_PATH.exists():
        print(f"""
Gmail OAuth Setup Required!

1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project (or use existing)
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Configure OAuth consent screen:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" for personal Gmail
   - Add yourself as a test user
5. Create OAuth 2.0 Client ID:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as the type
6. Download the JSON credentials
7. Save as: {CREDS_PATH}
8. Run this script again

Your email: {gmail.user_email}
""")
        return False

    return await gmail.initialize()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        if await setup_oauth():
            print("✅ Gmail OAuth setup complete!")

            # Test sending
            success = await send_report(
                "Email Bridge Active",
                "You can now reply to my emails and I will act on your instructions.",
            )
            print(f"Test email sent: {success}")

    asyncio.run(main())
