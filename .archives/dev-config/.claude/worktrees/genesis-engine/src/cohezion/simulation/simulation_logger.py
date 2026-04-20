import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset, Features, Sequence, Value, load_dataset


logger = logging.getLogger(__name__)


class SimulationLogger:
    """
    Handles sharded logging of simulation trajectories using Hugging Face datasets.

    This provides a structured way to store high-volume agent journeys,
    making them compatible with the HF ecosystem for later training or analysis.
    """

    def __init__(self, storage_dir: str = "data/simulations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_buffer: list[dict[str, Any]] = []
        self.batch_size = 100  # Flush every 100 cycles

        # Define features for consistency
        self.features = Features(
            {
                "timestamp": Value("string"),
                "cycle_id": Value("string"),
                "seed_thought": Value("string"),
                "universe_domain": Value("string"),
                "expert_synthesis": Value("string"),
                "hypothesis": Value("string"),
                "code": Value("string"),
                "outcome": Value("string"),
                "phi_score": Value("float32"),
                "state_trajectory": Sequence(Sequence(Value("float32"))),  # 12D vectors
                "narration": Value("string"),
                # Spatial extensions for Fractal Universe
                "spatial_pos": Sequence(Value("float32")),  # [x, y]
                "sector_type": Value("string"),
                "energy_level": Value("float32"),
            }
        )

    def log_cycle(self, data: dict[str, Any]):
        """Append a single simulation cycle to the buffer."""
        # Ensure timestamp
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()

        self.current_buffer.append(data)

        if len(self.current_buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """Persist current buffer to a sharded dataset file."""
        if not self.current_buffer:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.storage_dir / f"shard_{timestamp}.parquet"

        try:
            df = pd.DataFrame(self.current_buffer)
            dataset = Dataset.from_pandas(df, features=self.features)
            dataset.to_parquet(str(file_path))
            logger.info(f"💾 Sharded simulation log persisted: {file_path}")
            self.current_buffer = []
        except Exception as e:
            logger.error(f"❌ Failed to flush simulation logs: {e}")

    def load_universe_data(self, domain: str | None = None) -> Dataset:
        """Load all persisted shards into a single dataset, optionally filtered by domain."""
        files = list(self.storage_dir.glob("*.parquet"))
        if not files:
            return Dataset.from_dict({}, features=self.features)

        dataset = load_dataset("parquet", data_files=[str(f) for f in files], split="train")

        if domain:
            dataset = dataset.filter(lambda x: x["universe_domain"] == domain)

        return dataset

    def export_to_hub(self, repo_id: str, private: bool = True):
        """Export the entire dataset to the Hugging Face Hub."""
        dataset = self.load_universe_data()
        if len(dataset) > 0:
            dataset.push_to_hub(repo_id, private=private)
            logger.info(f"🚀 Simulation dataset exported to HF Hub: {repo_id}")
        else:
            logger.warning("⚠️ No simulation data found to export.")

    @classmethod
    def from_logs(cls, log_path: str, storage_dir: str = "data/simulations"):
        """Utility to bootstrap a dataset from existing text logs."""
        # TODO: Implement parser for lab_driver.log
        pass
