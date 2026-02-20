import json
from pathlib import Path

import ijson


SOURCE_FILE = Path("data/sim_results_25m.json")
OUTPUT_DIR = Path("data/ingest_chunks")
CHUNK_SIZE = 50000


def explode_dataset():
    if not SOURCE_FILE.exists():
        print(f"Source file {SOURCE_FILE} not found!")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Exploding {SOURCE_FILE} into chunks of {CHUNK_SIZE}...")

    chunk_idx = 0
    buffer = []

    with open(SOURCE_FILE, "rb") as f:
        # Stream 'journey.item'
        objects = ijson.items(f, "journey.item")

        for record in objects:
            buffer.append(record)

            if len(buffer) >= CHUNK_SIZE:
                _write_chunk(chunk_idx, buffer)
                chunk_idx += 1
                buffer = []

        if buffer:
            _write_chunk(chunk_idx, buffer)


from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _write_chunk(idx, data):
    filename = OUTPUT_DIR / f"chunk_{idx:04d}.jsonl"
    print(f"Writing {filename} ({len(data)} records)...")
    with open(filename, "w") as f:
        for item in data:
            f.write(json.dumps(item, cls=DecimalEncoder) + "\n")


if __name__ == "__main__":
    explode_dataset()
