"""Collect execution experiences from Parquet, SurrealDB, and vault sources.

Three tiers, each non-blocking:
  Tier 1: Parquet journey shards  (data/journeys/shard_*.parquet)
  Tier 2: SurrealDB mission_journey table
  Tier 3: Vault experiment JSON files

Execution logging:
  Compound executions can be logged via log_execution() to
  data/flume/experiences/execution_log.jsonl for future training.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)

# Default paths
_PARQUET_DIR = Path("data/journeys")
_VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "experiments"
_EXECUTION_LOG_DIR = Path("data/flume/experiences")


class ExperienceCollector:
    """Gather execution experiences from all available data sources.

    Parameters
    ----------
    parquet_dir : Path
        Directory containing ``shard_*.parquet`` files.
    vault_dir : Path
        Directory containing vault experiment JSON files.
    execution_log_dir : Path
        Directory for compound execution JSONL log.
    """

    def __init__(
        self,
        parquet_dir: Path | str = _PARQUET_DIR,
        vault_dir: Path | str = _VAULT_DIR,
        execution_log_dir: Path | str = _EXECUTION_LOG_DIR,
    ) -> None:
        self.parquet_dir = Path(parquet_dir)
        self.vault_dir = Path(vault_dir)
        self.execution_log_dir = Path(execution_log_dir)

    def collect_all(self, max_samples: int = 100_000) -> list[dict]:
        """Collect experiences from all tiers.

        Returns a list of normalized experience dicts with keys matching
        the ExperienceEncoder schema.
        """
        records: list[dict] = []
        records.extend(self._collect_parquet(max_samples))
        if len(records) < max_samples:
            records.extend(self._collect_surreal(max_samples - len(records)))
        if len(records) < max_samples:
            records.extend(self._collect_vault(max_samples - len(records)))
        logger.info("Collected %d total experience records", len(records))
        return records[:max_samples]

    # ------------------------------------------------------------------
    # Tier 1: Parquet shards
    # ------------------------------------------------------------------
    def _collect_parquet(self, max_samples: int) -> list[dict]:
        """Read journey shards from Parquet files."""
        if not self.parquet_dir.is_dir():
            logger.debug("Parquet dir %s not found, skipping tier 1", self.parquet_dir)
            return []
        parquet_files = sorted(self.parquet_dir.glob("shard_*.parquet"))
        if not parquet_files:
            return []

        try:
            import pyarrow.parquet as pq
        except ImportError:
            logger.debug("pyarrow not installed, skipping parquet tier")
            return []

        records: list[dict] = []
        for pf in parquet_files:
            if len(records) >= max_samples:
                break
            try:
                table = pq.read_table(pf)
                for _ in table.to_pydict().values():
                    # pydict returns {col: [values]} — need to iterate rows
                    break  # just need to check structure
                df_rows = table.to_pandas().to_dict(orient="records")
                for row in df_rows:
                    if len(records) >= max_samples:
                        break
                    records.append(self._normalize_parquet_row(row))
            except Exception as e:
                logger.debug("Skipping %s: %s", pf, e)
        logger.info("Tier 1 (parquet): collected %d records", len(records))
        return records

    @staticmethod
    def _compute_trajectory_stats(
        state_traj: list | np.ndarray | None,
    ) -> tuple[np.ndarray, float, float]:
        """Compute trajectory point + temporal statistics from full state_trajectory.

        Returns (last_12d_point, smoothness, convergence).
        - smoothness: 1.0 - mean absolute change across all 12D parameters (fabric stability)
        - convergence: 1.0 - std of last 3 trajectory norms (HIHO approach rate)
        """
        trajectory = np.zeros(12, dtype=np.float32)
        smoothness = 1.0  # default for single/no points
        convergence = 1.0

        if state_traj is None or len(state_traj) == 0:
            return trajectory, smoothness, convergence

        # Convert to array of 12D points
        points = []
        for pt in state_traj:
            arr = np.asarray(pt, dtype=np.float32).ravel()
            padded = np.zeros(12, dtype=np.float32)
            n = min(len(arr), 12)
            padded[:n] = arr[:n]
            points.append(padded)

        # Last point as trajectory
        trajectory = points[-1].copy()

        if len(points) > 1:
            pts_arr = np.array(points)
            # Smoothness: 1.0 - mean absolute change across fabric dimensions
            diffs = np.diff(pts_arr, axis=0)
            smoothness = float(np.clip(1.0 - np.mean(np.abs(diffs)), 0.0, 1.0))
            # Convergence: 1.0 - std of last 3 norms (HIHO approach stability)
            tail = pts_arr[-min(3, len(pts_arr)) :]
            norms = np.linalg.norm(tail, axis=1)
            convergence = float(np.clip(1.0 - np.std(norms), 0.0, 1.0))

        return trajectory, smoothness, convergence

    @staticmethod
    def _normalize_parquet_row(row: dict) -> dict:
        """Convert a parquet row into the canonical experience schema."""
        trajectory, smoothness, convergence = ExperienceCollector._compute_trajectory_stats(row.get("state_trajectory"))

        return {
            "trajectory": trajectory,
            "mission_id": row.get("mission_id", ""),
            "agent_id": row.get("agent_id", ""),
            "skill_name": row.get("skill_name", ""),
            "input_preview": row.get("input_preview", ""),
            "phi_score": float(row.get("phi_score", 0.0)),
            "novelty": float(row.get("novelty", 0.0)),
            "operation_type": "generate",  # default for journeys
            "trajectory_smoothness": smoothness,
            "trajectory_convergence": convergence,
        }

    # ------------------------------------------------------------------
    # Tier 2: SurrealDB mission_journey
    # ------------------------------------------------------------------
    def _collect_surreal(self, max_samples: int) -> list[dict]:
        """Query SurrealDB for mission journey records (non-blocking)."""
        try:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Already inside an async context — can't nest run_until_complete.
                # Skip SurrealDB tier; it'll be tried next session.
                logger.debug("SurrealDB tier skipped: event loop already running")
                return []

            return asyncio.run(self._collect_surreal_async(max_samples))
        except Exception as e:
            logger.debug("SurrealDB tier skipped: %s", e)
            return []

    async def _collect_surreal_async(self, max_samples: int) -> list[dict]:
        """Async SurrealDB collection."""
        try:
            from cohezion.core.persistence.surreal_client import SurrealClient

            client = SurrealClient()
            await client.connect()
            result = await client.query(f"SELECT * FROM mission_journey LIMIT {max_samples}")
            records = []
            if result and isinstance(result, list):
                for row in result:
                    if isinstance(row, dict):
                        records.append(self._normalize_surreal_row(row))
            logger.info("Tier 2 (surreal): collected %d records", len(records))
            return records
        except Exception as e:
            logger.debug("SurrealDB query failed: %s", e)
            return []

    @staticmethod
    def _normalize_surreal_row(row: dict) -> dict:
        """Normalize a SurrealDB mission_journey record."""
        trajectory, smoothness, convergence = ExperienceCollector._compute_trajectory_stats(row.get("state_trajectory"))

        return {
            "trajectory": trajectory,
            "mission_id": row.get("id", row.get("mission_id", "")),
            "agent_id": row.get("agent_id", ""),
            "skill_name": row.get("skill_name", ""),
            "input_preview": "",
            "phi_score": float(row.get("phi_score", 0.0)),
            "operation_type": row.get("operation_type", "generate"),
            "trajectory_smoothness": smoothness,
            "trajectory_convergence": convergence,
        }

    # ------------------------------------------------------------------
    # Tier 3: Vault experiment JSONs
    # ------------------------------------------------------------------
    def _collect_vault(self, max_samples: int) -> list[dict]:
        """Walk vault experiment files for experience data."""
        if not self.vault_dir.is_dir():
            logger.debug("Vault dir %s not found, skipping tier 3", self.vault_dir)
            return []

        records: list[dict] = []
        for json_path in sorted(self.vault_dir.rglob("*.json")):
            if len(records) >= max_samples:
                break
            try:
                with open(json_path) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    records.append(self._normalize_vault_record(data, json_path.stem))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and len(records) < max_samples:
                            records.append(self._normalize_vault_record(item, json_path.stem))
            except Exception as e:
                logger.debug("Skipping vault file %s: %s", json_path, e)

        logger.info("Tier 3 (vault): collected %d records", len(records))
        return records

    @staticmethod
    def _normalize_vault_record(record: dict, source: str) -> dict:
        """Normalize a vault experiment JSON into the canonical schema."""
        return {
            "trajectory": np.zeros(12, dtype=np.float32),
            "mission_id": record.get("id", source),
            "agent_id": record.get("agent_id", ""),
            "skill_name": record.get("skill_name", record.get("title", "")),
            "input_preview": record.get("hypothesis", record.get("description", "")),
            "phi_score": float(record.get("phi_score", 0.0)),
            "operation_type": record.get("operation_type", "analyze"),
        }

    # ------------------------------------------------------------------
    # Execution logging (compound loop → training data)
    # ------------------------------------------------------------------
    def log_execution(
        self,
        task_description: str,
        operation_type: str,
        metrics: dict,
        skill_name: str,
    ) -> None:
        """Append a compound execution record to the JSONL execution log.

        Creates data/flume/experiences/execution_log.jsonl (or configured
        path) for periodic re-embedding and VAE fine-tuning.
        """
        self.execution_log_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_description": task_description,
            "operation_type": operation_type,
            "metrics": metrics,
            "skill_name": skill_name,
        }
        log_file = self.execution_log_dir / "execution_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.debug("Logged execution: skill=%s op=%s", skill_name, operation_type)
