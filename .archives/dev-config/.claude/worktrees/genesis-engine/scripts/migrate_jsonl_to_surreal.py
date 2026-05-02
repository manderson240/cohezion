#!/usr/bin/env python3
"""Migrate JSONL fallback data to SurrealDB.

Run after SurrealDB is confirmed online:
    uv run python scripts/migrate_jsonl_to_surreal.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

JSONL_DIR = Path("data/mass_sim/checkpoints/jsonl")

TABLE_MAP = {
    "mass_sim_run": "mass_sim_run",
    "sim_universe_summary": "sim_universe_summary",
    "sim_checkpoint": "sim_checkpoint",
    "sim_analysis_report": "sim_analysis_report",
    "sim_artifact": "sim_artifact",
}


async def main() -> int:
    try:
        from surrealdb import AsyncSurreal
    except ImportError:
        logger.error("surrealdb package not installed: uv pip install surrealdb")
        return 1

    async with AsyncSurreal("ws://localhost:8000/rpc") as db:
        await db.signin({"username": "root", "password": "root"})
        await db.use("cohezion", "universe")
        logger.info("Connected to SurrealDB")

        # Apply schema if needed
        from cohezion.mass_sim.persistence import MASS_SIM_SCHEMA

        await db.query(MASS_SIM_SCHEMA)

        total = 0
        for jsonl_file in sorted(JSONL_DIR.glob("*.jsonl")):
            table = jsonl_file.stem
            if table not in TABLE_MAP:
                logger.warning(f"Unknown table: {table}, skipping")
                continue

            records = []
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

            if not records:
                continue

            logger.info(f"Migrating {len(records)} records to {table}...")
            for record in records:
                try:
                    await db.query(
                        f"CREATE {table} CONTENT $data",
                        {"data": record},
                    )
                    total += 1
                except Exception as e:
                    logger.warning(f"  Failed: {e}")

        logger.info(f"Migration complete: {total} records written to SurrealDB")

        # Rename JSONL files to .migrated
        for jsonl_file in JSONL_DIR.glob("*.jsonl"):
            jsonl_file.rename(jsonl_file.with_suffix(".jsonl.migrated"))
            logger.info(f"  Archived: {jsonl_file.name} -> .migrated")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
