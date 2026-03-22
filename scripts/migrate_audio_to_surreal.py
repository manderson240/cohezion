#!/usr/bin/env python3
"""
Migrate Audio Scripts to SurrealDB

Migrates existing filesystem audio scripts to the SurrealDB database,
then removes the original files to clean up Git status.

Usage:
    uv run python scripts/migrate_audio_to_surreal.py [--dry-run]
"""

import argparse
import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)


logger = logging.getLogger(__name__)

# Source directories to migrate
AUDIO_DIRS = [
    Path("src/cohezion/knowledge_graph/universe_nodes/plasma_theosophy/audio_scripts"),
]


def extract_metadata_from_filename(filename: str) -> dict:
    """Extract timestamp and index from audio script filename."""
    # Pattern: audio_1768733563_0.txt
    match = re.match(r"audio_(\d+)_(\d+)\.txt", filename)
    if match:
        timestamp = int(match.group(1))
        index = int(match.group(2))
        return {"timestamp": timestamp, "index": index}
    return {"timestamp": 0, "index": 0}


def parse_audio_script(content: str) -> dict:
    """Parse audio script content to extract case and score."""
    case_match = re.search(r"Case ([^.]+)\.\.\.", content)
    score_match = re.search(r"Score ([\d.]+)", content)

    score = 0.0
    if score_match:
        score_str = score_match.group(1).rstrip(".")  # Remove trailing periods
        try:
            score = float(score_str)
        except ValueError:
            score = 0.0

    return {
        "case_name": case_match.group(1) if case_match else "unknown",
        "score": score,
    }


async def migrate_directory(
    client: SurrealClient,
    audio_dir: Path,
    dry_run: bool = False,
    batch_size: int = 1000,
) -> tuple[int, int]:
    """Migrate a single audio_scripts directory to SurrealDB."""
    if not audio_dir.exists():
        logger.warning(f"Directory not found: {audio_dir}")
        return 0, 0

    files = list(audio_dir.glob("*.txt"))
    total = len(files)
    migrated = 0
    errors = 0

    logger.info(f"Found {total} files in {audio_dir}")

    for i, file_path in enumerate(files):
        try:
            content = file_path.read_text()
            meta = extract_metadata_from_filename(file_path.name)
            parsed = parse_audio_script(content)

            node = UniverseNode(
                id=f"audio_{meta['timestamp']}_{meta['index']}",
                content=content,
                node_type="audio_script",
                physics_state=PhysicsState(
                    time=float(meta["timestamp"]),
                    coherence=parsed["score"],
                    stability=parsed["score"],
                ),
                created_at=datetime.fromtimestamp(meta["timestamp"]),
                metadata={
                    "case_name": parsed["case_name"],
                    "score": parsed["score"],
                    "source_file": str(file_path),
                },
            )

            if not dry_run:
                await client.store_node(node)
                file_path.unlink()  # Delete after successful insert

            migrated += 1

            if (i + 1) % batch_size == 0:
                logger.info(f"Progress: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

        except Exception as e:
            logger.error(f"Failed to migrate {file_path}: {e}")
            errors += 1

    return migrated, errors


async def main():
    parser = argparse.ArgumentParser(description="Migrate audio scripts to SurrealDB")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--batch-size", type=int, default=1000, help="Logging frequency")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.dry_run:
        logger.info("DRY RUN MODE - no changes will be made")

    # Connect to SurrealDB
    client = SurrealClient(
        url="ws://localhost:8000/rpc",
        namespace="cohezion",
        database="universe",
    )

    if not await client.connect():
        logger.error("Failed to connect to SurrealDB")
        return

    # Ensure schema exists
    await client.setup_schema()

    total_migrated = 0
    total_errors = 0

    for audio_dir in AUDIO_DIRS:
        migrated, errors = await migrate_directory(client, audio_dir, args.dry_run, args.batch_size)
        total_migrated += migrated
        total_errors += errors

    await client.close()

    logger.info(f"Migration complete: {total_migrated} migrated, {total_errors} errors")

    if not args.dry_run and total_migrated > 0:
        logger.info("Run 'git status --porcelain | wc -l' to verify cleanup")


if __name__ == "__main__":
    asyncio.run(main())
