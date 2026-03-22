"""Knowledge Base Migration to SurrealDB.

Migrates harvested journal entries and agent journeys into the
SurrealDB-backed version registry and knowledge graph.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from cohezion.release.surreal_version_registry import SurrealVersionRegistry
from cohezion.release.version_registry import RegistryEntry


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

HARVEST_PATH = Path("vault/historical_harvest")


async def migrate_journals() -> None:
    """Migrate harvested journals to SurrealDB."""
    registry = SurrealVersionRegistry()
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

                # Create a registry entry for this historical event
                entry = RegistryEntry(
                    version=f"hist-{h}",
                    bump_type="PATCH",
                    release_date=dt,
                    epic_ids=[],
                    story_ids=[],
                    author="historical-harvest",
                    changelog_diff=content,
                )

                try:
                    await registry.record(entry)
                    count += 1
                except ValueError as e:
                    if "already exists" in str(e):
                        continue
                    raise
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
