import asyncio
import logging
from datetime import datetime
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [CHRONICLER] - %(message)s"
)
logger = logging.getLogger("Chronicler")

HISTORY_FILE = Path("data/UNIVERSE_HISTORY.md")


class Chronicler:
    """
    The Chronicler: Writes the history of the Universe Simulation.
    Polls the database for Milestones and Missions to generate a persistent log.
    """

    def __init__(self):
        self.db = SurrealClient()
        self.last_timestamp = (
            datetime.now().isoformat()
        )  # Start from NOW (ignore ancient history for live run)
        # Or should we replay? Let's replay from file check.

        if HISTORY_FILE.exists():
            # In a real app we'd parse the last timestamp from the file.
            # For now, let's just grab "recent" events (last 1 hour?) to avoid re-dumping everything
            pass
        else:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            HISTORY_FILE.write_text("# UNIVERSE SIMULATION HISTORY\n\n")

    async def run_loop(self):
        logger.info("📜 Chronicler Watching Threads of Fate...")

        while True:
            try:
                await self.chronicle()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Ink spilled: {e}")
                await asyncio.sleep(5)

    async def chronicle(self):
        # Query for Milestones and Completed Missions created AFTER last check
        # SurrealQL: created_at > $timestamp
        query = f"SELECT * FROM universe_nodes WHERE (node_type = 'milestone' OR (node_type = 'mission' AND metadata.status = 'COMPLETED')) AND created_at > '{self.last_timestamp}' ORDER BY created_at ASC"

        response = await self.db.query(query)
        items = []
        if isinstance(response, list) and response and isinstance(response[0], dict):
            items = response[0].get("result", [])

        if not items:
            return

        new_entries = []
        for item in items:
            node_type = item.get("node_type")
            meta = item.get("metadata", {})
            timestamp = item.get("created_at", str(datetime.now()))

            # Update cursor
            if timestamp > self.last_timestamp:
                self.last_timestamp = timestamp

            # Format Entry
            icon = "🏆" if node_type == "milestone" else "✅"
            topic = meta.get("topic", "Unknown Event")
            content = item.get("content", "")

            entry = f"- **[{timestamp[:19]}]** {icon} **{topic}**: {content}"
            new_entries.append(entry)
            logger.info(f"Writing to History: {topic}")

        if new_entries:
            with open(HISTORY_FILE, "a") as f:
                f.write("\n".join(new_entries) + "\n")


if __name__ == "__main__":

    async def main():
        scribe = Chronicler()
        await scribe.run_loop()

    asyncio.run(main())
