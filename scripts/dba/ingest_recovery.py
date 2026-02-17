import asyncio
import json
import logging
from pathlib import Path

from cohezion.core.persistence.admin import DBAdmin


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestRecovery")

RECOVERY_DIR = Path("/home/mike-anderson/dev/cohezion/data/overnight")
BATCH_SIZE = 500


async def ingest_recovery():
    dba = DBAdmin()
    await dba.connect()

    logger.info(f"🚀 Starting Recovery Ingestion from {RECOVERY_DIR}")

    # scan for json files
    # We focus on the 'responses.json' and 'results.json' files which seem to contain the meat
    files = list(RECOVERY_DIR.glob("**/responses.json")) + list(RECOVERY_DIR.glob("**/results.json"))

    logger.info(f"Found {len(files)} primary data files.")

    total_records = 0

    for file_path in files:
        logger.info(f"Processing {file_path.name}...")
        try:
            with open(file_path) as f:
                # Check if it's a list or individual objects (JSONL vs JSON)
                # Assuming JSON list based on previous context, but will handle both
                first_char = f.read(1)
                f.seek(0)

                data = []
                if first_char == "[":
                    data = json.load(f)
                elif first_char == "{":
                    # Maybe JSONL
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))

                if not data:
                    logger.warning(f"File {file_path.name} was empty or unparseable.")
                    continue

                # Ingest
                # We interpret these as 'simulation_events' or 'agent_trajectories'
                # Let's verify the table name. 'velocity_events' was high freq, 'agent_journeys' was low freq.
                # If these are massive dump files, they might be the raw physics events.
                # Let's dump them into a 'recovery_archive' table first to be safe,
                # or map them if we know the schema.

                # DBA Decision: Safe Import.
                table_name = "recovery_archive"

                # clean data
                cleaned_data = []
                for item in data:
                    if isinstance(item, dict):
                        # Add metadata about recovery source
                        item["_recovery_source"] = str(file_path)
                        cleaned_data.append(item)

                await dba.batch_ingest(table_name, cleaned_data, batch_size=BATCH_SIZE)
                total_records += len(cleaned_data)

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")

    logger.info(f"🎉 Recovery Complete. Ingested {total_records} records into '{table_name}'.")
    await dba.close()


if __name__ == "__main__":
    asyncio.run(ingest_recovery())
