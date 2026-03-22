import asyncio
import json
import logging
import os
from pathlib import Path

from cohezion.core.persistence.admin import DBAdmin


# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MassIngest] - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("mass_ingest.log"), logging.StreamHandler()],
)
logger = logging.getLogger("MassIngest")

# Config
SOURCE_ROOT = Path("/home/mike-anderson/dev/cohezion/data/restored_simulations")
BATCH_SIZE = 1000
MAX_CONCURRENCY = 10
DELETE_ON_SUCCESS = True


async def process_batch(dba: DBAdmin, file_batch: list[Path]):
    """
    Reads a batch of files, ingests them, and deletes them on success.
    """
    records = []
    valid_files = []

    # Read files (IO bound, use executor if needed, but for small JSONs direct read is often fine)
    # We'll do direct read for simplicity and verify performance.
    for p in file_batch:
        try:
            with open(p) as f:
                content = f.read().strip()
                if not content:
                    continue

                # Try parsing
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # Maybe it's not JSON, or corrupted?
                    # Log and skip
                    logger.warning(f"Invalid JSON in {p}")
                    continue

                # Normalize to list
                if isinstance(data, dict):
                    # Inject filepath as ID/metadata if missing
                    if "id" not in data:
                        # Use filename as ID?
                        # data['id'] = p.stem
                        pass
                    data["_source_file"] = str(p)
                    records.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item["_source_file"] = str(p)
                            records.append(item)

                valid_files.append(p)

        except Exception as e:
            logger.error(f"Error reading {p}: {e}")

    if not records:
        return 0

    # Ingest
    # Determine table name based on directory?
    # For now, generic `universe_nodes` or `restored_nodes`.
    # Let's check the path.
    # If path has 'plasma_theosophy', use that as table or tag?
    # User had these in `universe_nodes` directory. They likely belong to `universe_nodes` table.
    table_name = "universe_nodes"

    success, errors = await dba.batch_ingest(table_name, records, batch_size=len(records))

    if errors == 0 and DELETE_ON_SUCCESS:
        # Delete processed files
        for p in valid_files:
            try:
                p.unlink()
            except Exception as e:
                logger.error(f"Failed to delete {p}: {e}")

    return success


async def mass_ingest():
    dba = DBAdmin()
    await dba.connect()

    queue = asyncio.Queue(maxsize=MAX_CONCURRENCY * 2)

    # Producer
    async def producer():
        batch = []
        count = 0
        # Walk recursively
        for root, _dirs, files in os.walk(SOURCE_ROOT):
            for file in files:
                if file.endswith(".json") or file.endswith(".jsonl") or file.endswith(".txt"):
                    batch.append(Path(root) / file)
                    if len(batch) >= BATCH_SIZE:
                        await queue.put(list(batch))
                        batch = []
                        count += 1
                        if count % 10 == 0:
                            logger.info(f"Queued {count * BATCH_SIZE} files...")

        if batch:
            await queue.put(batch)

        # Sentinel
        for _ in range(MAX_CONCURRENCY):
            await queue.put(None)

    # Consumer
    async def consumer(worker_id):
        total_ingested = 0
        while True:
            batch = await queue.get()
            if batch is None:
                queue.task_done()
                break

            try:
                n = await process_batch(dba, batch)
                total_ingested += n
            except Exception as e:
                logger.error(f"Worker {worker_id} failed batch: {e}")

            queue.task_done()
        return total_ingested

    # Start Producer
    prod_task = asyncio.create_task(producer())

    # Start Consumers
    consumers = [asyncio.create_task(consumer(i)) for i in range(MAX_CONCURRENCY)]

    # Wait
    await prod_task
    results = await asyncio.gather(*consumers)

    logger.info(f"🎉 Total Ingested: {sum(results)}")

    await dba.close()


if __name__ == "__main__":
    if not SOURCE_ROOT.exists():
        logger.error(f"Source root {SOURCE_ROOT} does not exist yet. Waiting for restore...")
    else:
        asyncio.run(mass_ingest())
