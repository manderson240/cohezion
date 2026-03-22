import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import aiofiles


# Add src to sys.path to find DBAdmin
sys.path.append(str(Path.cwd() / "src"))
from cohezion.core.persistence.admin import DBAdmin


# Config
BATCH_SIZE = 2000
INGEST_DIR = Path("data/ingest_chunks")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MIGRATE] - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("migration_v2.log"), logging.StreamHandler()],
)
logger = logging.getLogger("MigrationV2")


async def process_jsonl_file(file_path: Path):
    """
    Reads a JSONL file and returns list of records.
    """
    records = []
    try:
        async with aiofiles.open(file_path) as f:
            async for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if "ingest_time" not in record:
                            record["ingest_time"] = time.time()
                        records.append(record)
                    except ValueError:
                        pass
        return records
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return []


async def main():
    logger.info("Starting Mass Migration V2 (Chunked)...")

    if not INGEST_DIR.exists():
        logger.error(f"Ingest directory {INGEST_DIR} not found! Run explode_json.py first.")
        return

    files = sorted([f for f in INGEST_DIR.iterdir() if f.suffix == ".jsonl"])
    total_files = len(files)
    logger.info(f"Found {total_files} chunk files to ingest.")

    dba = DBAdmin()
    await dba.connect()

    total_ingested = 0
    start_time = time.time()

    for idx, file_path in enumerate(files):
        logger.info(f"Processing chunk {idx + 1}/{total_files}: {file_path.name}")

        batch = await process_jsonl_file(file_path)
        if not batch:
            continue

        success_count, _error_count = await dba.batch_ingest("universe_nodes", batch, batch_size=BATCH_SIZE)
        total_ingested += success_count

        # Calculate rate
        elapsed = time.time() - start_time
        rate = total_ingested / elapsed if elapsed > 0 else 0
        logger.info(f"Progress: {total_ingested} records. Rate: {rate:.2f} rec/s")

        # Optional: Delete chunk after successful ingest to save space?
        # file_path.unlink()

        # Optional: Delete chunk after successful ingest to save space?
        # file_path.unlink()

    logger.info(
        f"Migration Complete. Total: {total_ingested}. Time: {time.time() - start_time:.2f}s"
    )
    await dba.close()


if __name__ == "__main__":
    asyncio.run(main())
