"""Knowledge Base Migration to SurrealDB (Direct SQL).

Migrates harvested journal entries into SurrealDB using direct SQL queries
via the SurrealClient.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from cohezion.core.persistence.surreal_client import get_surreal_client


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

HARVEST_PATH = Path("vault/historical_harvest")


async def migrate_journals() -> None:
    """Migrate harvested journals to SurrealDB using direct queries."""
    client = get_surreal_client()
    await client.connect()

    journal_dir = HARVEST_PATH / "journals"
    if not journal_dir.exists():
        logger.warning(f"Journal harvest directory not found: {journal_dir}")
        return

    logger.info("Migrating harvested journals...")

    count = 0
    # Walk through branch-specific folders
    for branch_dir in journal_dir.iterdir():
        if not branch_dir.is_dir():
            continue

        logger.info(f"Processing branch: {branch_dir.name}")

        for journal_file in branch_dir.glob("*.md"):
            try:
                content = journal_file.read_text()
                # Heuristic: file name starts with date like 2026-01-19
                date_str = journal_file.name.split("_")[0]
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                except ValueError:
                    dt = datetime.fromtimestamp(journal_file.stat().st_mtime, tz=UTC)

                # Use content hash for unique version to avoid duplicate migrations
                h = hashlib.sha256(content.encode()).hexdigest()[:12]
                version = f"hist-{h}"

                # Check for existing version
                res = await client.query(
                    "SELECT * FROM version_registry WHERE version = $v", {"v": version}
                )
                if res and res[0]:
                    continue

                # Create entry using SQL
                data = {
                    "version": version,
                    "previous_version": None,
                    "bump_type": "PATCH",
                    "release_date": dt.isoformat(),
                    "epic_ids": [],
                    "story_ids": [],
                    "author": "historical-harvest",
                    "changelog_diff": content,
                    "prd_traces": [],
                    "security_alerts": [],
                }

                await client.query("CREATE version_registry CONTENT $data", {"data": data})
                count += 1
                logger.info(f"Recorded version {version}")
            except Exception as e:
                logger.error(f"Failed to migrate {journal_file}: {e}")

    logger.info(f"Successfully migrated {count} historical journal entries to SurrealDB.")


async def main() -> None:
    try:
        await migrate_journals()
    except Exception as e:
        logger.error(f"Migration failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
