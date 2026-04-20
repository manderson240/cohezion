import asyncio
import sys
from datetime import datetime
from pathlib import Path


# Add src to path
PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.core.persistence.surreal_client import SurrealClient


# Configuration
SURREAL_URL = "ws://localhost:8000/rpc"
NAMESPACE = "cohezion"
DATABASE = "logs"
LOG_FILES = [
    PROJECT_ROOT / "logs/cron_runs.log",
    PROJECT_ROOT / "logs/overnight_sprint_20260309_004122.log",
]


class LogSink:
    def __init__(self, client: SurrealClient):
        self.client = client
        self.positions = {}

    async def setup(self):
        # Create logs table
        schema = """
        DEFINE TABLE log_entries SCHEMAFULL;
        DEFINE FIELD timestamp ON TABLE log_entries TYPE datetime DEFAULT time::now();
        DEFINE FIELD source ON TABLE log_entries TYPE string;
        DEFINE FIELD message ON TABLE log_entries TYPE string;
        DEFINE FIELD level ON TABLE log_entries TYPE string DEFAULT 'INFO';
        DEFINE INDEX log_time_idx ON log_entries FIELDS timestamp;
        """
        await self.client.connect()
        # In SurrealDB 3.0, we can just run the query
        await self.client.query(schema)
        print(f"✅ SurrealDB 3.0 Log Sink initialized. (NS: {NAMESPACE}, DB: {DATABASE})")

    async def tail_file(self, file_path: Path):
        source_name = file_path.name
        if not file_path.exists():
            print(f"⚠️  Log file not found: {file_path}")
            return

        # Start from the end
        self.positions[file_path] = file_path.stat().st_size

        while True:
            if not file_path.exists():
                await asyncio.sleep(5)
                continue

            current_size = file_path.stat().st_size
            if current_size < self.positions[file_path]:
                # File rotated or truncated
                self.positions[file_path] = 0

            if current_size > self.positions[file_path]:
                with open(file_path) as f:
                    f.seek(self.positions[file_path])
                    lines = f.readlines()
                    self.positions[file_path] = f.tell()

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # Try to parse level
                        level = "INFO"
                        if "ERROR" in line:
                            level = "ERROR"
                        elif "WARN" in line:
                            level = "WARN"
                        elif "DEBUG" in line:
                            level = "DEBUG"

                        # Insert into SurrealDB
                        data = {
                            "source": source_name,
                            "message": line,
                            "level": level,
                            "timestamp": datetime.now().isoformat(),
                        }
                        try:
                            await self.client.create("log_entries", data)
                        except Exception as e:
                            print(f"❌ Failed to sink log line: {e}")

            await asyncio.sleep(1)

    async def run(self):
        await self.setup()
        tasks = [self.tail_file(f) for f in LOG_FILES]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    client = SurrealClient(url=SURREAL_URL, namespace=NAMESPACE, database=DATABASE)
    sink = LogSink(client)
    try:
        asyncio.run(sink.run())
    except KeyboardInterrupt:
        print("👋 Log sink stopped.")
