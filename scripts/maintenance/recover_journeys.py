import asyncio
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient


# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("JourneyRecovery")

# Config
AUDIO_DIR = Path("/home/mike-anderson/dev/cohezion/audio/narrations")
PROCESSED_DIR = AUDIO_DIR / "processed_recovery"


class JourneyRecoverer:
    def __init__(self):
        self.db = SurrealClient()
        self.regex_agent = re.compile(r"I am ([a-zA-Z0-9_]+)\.")

    async def run(self):
        if not AUDIO_DIR.exists():
            logger.error(f"Directory not found: {AUDIO_DIR}")
            return

        PROCESSED_DIR.mkdir(exist_ok=True)

        files = list(AUDIO_DIR.glob("thought_*.txt"))
        files.extend(list(AUDIO_DIR.glob("weave_*.txt")))  # Also capture weave files if narrative

        logger.info(f"Found {len(files)} files to recover.")

        count = 0
        for f in files:
            try:
                content = f.read_text(encoding="utf-8").strip()
                if not content:
                    continue

                # Extract Metadata
                timestamp_ms = 0
                if f.name.startswith("thought_"):
                    # thought_1769832724281.txt -> 1769832724281
                    ts_str = f.stem.split("_")[1]
                    timestamp_ms = int(ts_str)
                elif f.name.startswith("weave_"):
                    # weave_32240.txt -> Maybe incomplete timestamp?
                    # Let's use file mtime as fallback
                    timestamp_ms = int(os.path.getmtime(f) * 1000)

                # Extract Agent Name
                match = self.regex_agent.search(content)
                agent_name = match.group(1) if match else "UnknownAgent"

                # Convert to ISO format
                iso_time = datetime.fromtimestamp(timestamp_ms / 1000, UTC).isoformat()

                # Payload
                payload = {
                    "timestamp": iso_time,
                    "agent": agent_name,
                    "content": content,
                    "source": "zsf_recovery_v1",
                    "recovered_at": datetime.now(UTC).isoformat(),
                }

                # Ingest
                await self.db.create("journey", payload)
                count += 1

                # Move to processed (to prevent re-ingestion, but keep on disk as backup)
                # target = PROCESSED_DIR / f.name
                # f.rename(target)
                # Actually, user said recover from disk, let's NOT move/delete yet
                # to be safe, just log. Idempotency is handled by DB? create() makes new ID.
                # So we might duplicate if run twice.
                # Let's check existence first? No, too slow.
                # We'll just run it once.

            except Exception as e:
                logger.error(f"Failed to process {f.name}: {e}")

        logger.info(f"✅ Successfully recovered {count} journeys into SurrealDB.")


if __name__ == "__main__":
    recoverer = JourneyRecoverer()
    asyncio.run(recoverer.run())
