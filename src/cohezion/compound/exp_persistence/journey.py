import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset, Features, Sequence, Value

from cohezion.core.persistence.surreal_client import get_surreal_client


logger = logging.getLogger(__name__)


class JourneyPersistence:
    """
    Handles persistence of high-frequency mission trajectories.
    - Uses SurrealDB for checkpoints.
    - Uses sharded Parquet for high-volume raw metrics and trajectories.
    """

    def __init__(self, storage_dir: str = "data/journeys", batch_size: int = 50):
        self._db = None
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self.current_buffer: list[dict[str, Any]] = []

        # Define features for trajectory consistency (12D Flume support)
        self.features = Features(
            {
                "timestamp": Value("string"),
                "mission_id": Value("string"),
                "agent_id": Value("string"),
                "skill_name": Value("string"),
                "input_preview": Value("string"),
                "output_preview": Value("string"),
                "phi_score": Value("float32"),
                "novelty": Value("float32"),
                "flume_version": Value("string"),
                "state_trajectory": Sequence(Sequence(Value("float32"))),  # 12D vectors
            }
        )

    @property
    def db(self):
        if self._db is None:
            self._db = get_surreal_client()
        return self._db

    async def persist_batch(self, batch: list[dict[str, Any]]):
        """Coordinate persistence to SurrealDB and Parquet."""
        # 1. SurrealDB Persistence (Machine search/Checkpoints)
        await self._persist_to_surreal(batch)

        # 2. Sharded Parquet Persistence (High-volume telemetry)
        for data in batch:
            self.current_buffer.append(data)
            if len(self.current_buffer) >= self.batch_size:
                await self._flush_to_parquet()

    async def _persist_to_surreal(self, batch: list[dict[str, Any]]):
        """Persist a batch of mission data to SurrealDB."""
        for data in batch:
            try:
                mission_id = data.get("mission_id", "anonymous")
                record_id = f"mission_journey:{mission_id}"

                data["flume_version"] = "1.0"
                data["state_dimensions"] = 12

                if not self.db._connected:
                    await self.db.connect()

                await self.db.query(f"UPSERT {record_id} CONTENT $data", {"data": data})
                logger.debug(f"Persisted mission journey to Surreal: {mission_id}")
            except Exception as e:
                logger.error(f"SurrealDB persistence failed for mission {data.get('mission_id')}: {e}")

    async def _flush_to_parquet(self):
        """Persist current buffer to a sharded Parquet file."""
        if not self.current_buffer:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.storage_dir / f"shard_{timestamp}.parquet"

        try:
            # Prepare data for Parquet (ensure previews aren't massive)
            clean_batch = []
            for item in self.current_buffer:
                clean_item = {
                    "timestamp": item.get("timestamp", datetime.now().isoformat()),
                    "mission_id": item.get("mission_id", "unknown"),
                    "agent_id": item.get("agent_id", "unknown"),
                    "skill_name": item.get("skill_name", "unknown"),
                    "input_preview": str(item.get("prompt", ""))[:500],
                    "output_preview": str(item.get("response", ""))[:500],
                    "phi_score": float(item.get("phi_score", 0.0)),
                    "novelty": float(item.get("novelty", 1.0)),
                    "flume_version": "1.0",
                    "state_trajectory": item.get("state_trajectory", []),
                }
                clean_batch.append(clean_item)

            df = pd.DataFrame(clean_batch)
            dataset = Dataset.from_pandas(df, features=self.features)
            dataset.to_parquet(str(file_path))
            logger.info(f"💾 Sharded mission journey persisted: {file_path}")
            self.current_buffer = []
        except Exception as e:
            logger.error(f"❌ Failed to flush mission journey to Parquet: {e}")


def get_journey_persistence() -> JourneyPersistence:
    return JourneyPersistence()
