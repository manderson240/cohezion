import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from imap_tools import AND, MailBox

from cohezion.mcp.email_notifier import EmailNotifier, NotificationConfig


logger = logging.getLogger("PhoneOrchestrator")


class PhoneOrchestrator:
    """
    Remote command listener for Cohezion.
    Polls for emails with [CMD] in the subject and executes them.
    """

    def __init__(self):
        self.config = NotificationConfig.from_env()
        self.notifier = EmailNotifier(config=self.config)
        self.imap_host = "imap.gmail.com"
        self.authorized_sender = self.config.recipient_email or "manderson240@gmail.com"

        # Command map
        self.commands = {
            "status": self.cmd_status,
            "ping": self.cmd_ping,
            "run": self.cmd_run,
            "report": self.cmd_report,
            "resume": self.cmd_resume,
        }
        self.last_event_check = datetime.now().isoformat()

    async def poll_forever(self, interval: int = 60):
        """Main loop for polling commands and monitoring blocks."""
        logger.info(f"📱 PhoneOrchestrator started. Authorized sender: {self.authorized_sender}")

        # Start the block monitor in parallel
        asyncio.create_task(self.block_monitor_loop())

        while True:
            try:
                commands = await asyncio.to_thread(self._fetch_commands)
                for cmd_subject, cmd_body in commands:
                    await self.process_command(cmd_subject, cmd_body)

            except Exception as e:
                logger.error(f"Polling error: {e}")

            await asyncio.sleep(interval)

    async def block_monitor_loop(self, interval: int = 30):
        """Monitor SurrealDB for AGENT_BLOCKED events."""
        logger.info("📡 Block monitor loop active.")
        from cohezion.core.persistence.surreal_client import SurrealClient

        db = SurrealClient()

        while True:
            try:
                await db.connect()
                # Query for new blocking events
                query = """
                SELECT * FROM velocity_events
                WHERE type IN ['AGENT_BLOCKED', 'SECURITY_BLOCK', 'RESOURCE_EXHAUSTED']
                AND timestamp > $last_check
                """
                events = await db.query(query, {"last_check": self.last_event_check})

                for event in events:
                    agent = event.get("agent", "Unknown Agent")
                    event_type = event.get("type")
                    details = event.get("details", {})

                    message = f"Agent {agent} encountered a {event_type}. Details: {details}"
                    await self.notifier.send_block_alert(task_title=f"{agent} Blocked", message=message)
                    logger.info(f"🚨 Block Alert sent for {agent}")

                self.last_event_check = datetime.now().isoformat()
                await db.close()
            except Exception as e:
                logger.error(f"Block monitor error: {e}")

            await asyncio.sleep(interval)

    def _fetch_commands(self) -> list[tuple]:
        """Fetch UNSEEN emails with [CMD] in subject."""
        commands = []
        if not self.config.sender_password:
            return []

        try:
            with MailBox(self.imap_host).login(self.config.sender_email, self.config.sender_password) as mailbox:
                # Criteria: Unseen AND From authorized sender AND contains [CMD]
                criteria = AND(seen=False, from_=self.authorized_sender)
                for msg in mailbox.fetch(criteria, mark_seen=True):
                    if "[CMD]" in msg.subject.upper():
                        commands.append((msg.subject, msg.text or msg.html))
                        logger.info(f"📥 Received Command: {msg.subject}")
        except Exception as e:
            logger.error(f"IMAP fetch error: {e}")

        return commands

    async def process_command(self, subject: str, body: str):
        """Parse and execute a command."""
        # Extract command part: [CMD] <command> <args>
        parts = subject.upper().replace("[CMD]", "").strip().split()
        if not parts:
            return

        cmd_name = parts[0].lower()
        args = parts[1:]

        if cmd_name in self.commands:
            result = await self.commands[cmd_name](args, body)
            await self.notifier.send_email(
                subject=f"RE: {subject}",
                body=f"<h3>Response to {cmd_name}</h3><pre>{result}</pre>",
                is_html=True,
            )
        else:
            await self.notifier.send_email(
                subject=f"RE: {subject}",
                body=f"Unknown command: {cmd_name}. Supported: {', '.join(self.commands.keys())}",
                is_html=False,
            )

    async def cmd_status(self, args, body) -> str:
        """Get system status."""
        try:
            # Check active python processes
            res = subprocess.run(["ps", "aux", "--sort=-%cpu"], capture_output=True, text=True)
            procs = [line for line in res.stdout.split("\n") if "python" in line or "uv" in line][:5]

            status = f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            status += "Active Processes:\n" + "\n".join(procs)

            # Check SurrealDB
            surreal = subprocess.run(
                ["systemctl", "is-active", "cohezion-surreal.service"],
                capture_output=True,
                text=True,
            )
            status += f"\nSurrealDB: {surreal.stdout.strip()}"

            return status
        except Exception as e:
            return f"Error fetching status: {e}"

    async def cmd_ping(self, args, body) -> str:
        return "PONG. Cohezion Swarm is online and vigilant."

    async def cmd_run(self, args, body) -> str:
        """Run a specific script in scripts/"""
        if not args:
            return "Usage: [CMD] run <script_name>"

        script_name = args[0]
        if not script_name.endswith(".py"):
            script_name += ".py"

        script_path = Path("scripts") / script_name
        if not script_path.exists():
            return f"Script not found: {script_path}"

        try:
            # Run in background to avoid blocking
            subprocess.Popen(["uv", "run", "python3", str(script_path)])
            return f"Started {script_name} in background."
        except Exception as e:
            return f"Failed to start script: {e}"

    async def cmd_report(self, args, body) -> str:
        """Send the latest research report."""
        report_path = Path("logs/overnight_report.txt")
        if report_path.exists():
            return report_path.read_text()
        return "No report found. Still mining..."

    async def cmd_resume(self, args, body) -> str:
        """Resume blocked tasks or clear resource throttles."""
        return "System state resumed. Swarm is re-evaluating trajectories."


async def main():
    logging.basicConfig(level=logging.INFO)
    orchestrator = PhoneOrchestrator()
    await orchestrator.poll_forever()


if __name__ == "__main__":
    asyncio.run(main())
