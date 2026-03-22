"""SurrealDB persistence for mass simulation results.

Uses existing SurrealClient with circuit breaker fallback.
Batch writes via admin.batch_ingest for throughput.
Falls back to JSONL files when DB unavailable.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.mass_sim.config import (
        SimulationConfig,
        SimulationReport,
        UniverseResult,
    )



logger = logging.getLogger(__name__)

# New tables for mass simulation
MASS_SIM_SCHEMA = """
DEFINE TABLE mass_sim_run SCHEMALESS;
DEFINE INDEX idx_run_time ON mass_sim_run FIELDS created_at;

DEFINE TABLE sim_universe_summary SCHEMALESS;
DEFINE INDEX idx_summary_run ON sim_universe_summary FIELDS run_id;
DEFINE INDEX idx_summary_seed ON sim_universe_summary FIELDS seed;

DEFINE TABLE sim_checkpoint SCHEMALESS;
DEFINE INDEX idx_checkpoint_run ON sim_checkpoint FIELDS run_id;
DEFINE INDEX idx_checkpoint_universe ON sim_checkpoint FIELDS universe_id;

DEFINE TABLE sim_analysis_report SCHEMALESS;
DEFINE INDEX idx_report_run ON sim_analysis_report FIELDS run_id;

DEFINE TABLE sim_artifact SCHEMALESS;
DEFINE INDEX idx_artifact_run ON sim_artifact FIELDS run_id;

DEFINE TABLE sim_journey_narrative SCHEMALESS;
DEFINE INDEX idx_narrative_run ON sim_journey_narrative FIELDS run_id;
DEFINE INDEX idx_narrative_universe ON sim_journey_narrative FIELDS universe_id;

DEFINE TABLE pipeline_run SCHEMALESS;
DEFINE INDEX idx_pipeline_time ON pipeline_run FIELDS created_at;

DEFINE TABLE training_checkpoint SCHEMALESS;
DEFINE INDEX idx_training_run ON training_checkpoint FIELDS run_id;
DEFINE INDEX idx_training_type ON training_checkpoint FIELDS training_type;

DEFINE TABLE hyperparameter_search SCHEMALESS;
DEFINE INDEX idx_search_run ON hyperparameter_search FIELDS run_id;
DEFINE INDEX idx_search_iter ON hyperparameter_search FIELDS iteration;
"""


class SimulationPersistence:
    """Persist mass simulation results to SurrealDB or JSONL fallback."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self._db = None
        self._fallback_dir = config.checkpoint_dir / "jsonl"
        self._fallback_dir.mkdir(parents=True, exist_ok=True)

    async def _get_db(self):
        """Lazy-load SurrealClient."""
        if not self.config.persist_to_db:
            return None
        if self._db is None:
            try:
                from cohezion.core.persistence.surreal_client import SurrealClient

                self._db = SurrealClient()
                await self._db.connect()
                # Apply schema migration
                await self._db.query(MASS_SIM_SCHEMA)
                logger.info("SurrealDB connected for mass simulation")
            except Exception as e:
                logger.warning(f"SurrealDB unavailable, using JSONL fallback: {e}")
                self._db = None
        return self._db

    async def store_run_metadata(self, run_id: str, config: SimulationConfig) -> None:
        """Store simulation run configuration."""
        record = {
            "id": run_id,
            "scale_tier": config.scale.name,
            "n_agents": config.scale.n_agents,
            "n_epochs": config.scale.n_epochs,
            "n_universes": config.scale.n_universes,
            "use_navigator": config.use_navigator,
            "agent_seed": config.agent_seed_base,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        db = await self._get_db()
        if db:
            try:
                await db.query(
                    "CREATE mass_sim_run CONTENT $data",
                    {"data": record},
                )
            except Exception as e:
                logger.warning(f"DB write failed: {e}")
                self._write_jsonl("mass_sim_run", record)
        else:
            self._write_jsonl("mass_sim_run", record)

    async def store_universe_result(self, run_id: str, result: UniverseResult) -> None:
        """Store per-universe summary and checkpoints."""
        # Universe summary
        summary = {
            "run_id": run_id,
            "universe_id": result.universe_id,
            "seed": result.seed,
            "n_agents": result.n_agents,
            "n_epochs": result.n_epochs,
            "mean_coherence": result.final_stats.get("mean_coherence", 0),
            "pct_within_bounds": result.final_stats.get("pct_within_bounds", 0),
            "mean_norm": result.final_stats.get("mean_norm", 0),
            "elapsed_seconds": result.elapsed_seconds,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        db = await self._get_db()
        if db:
            try:
                await db.query(
                    "CREATE sim_universe_summary CONTENT $data",
                    {"data": summary},
                )
                # Store sparse checkpoints (every 5th to save DB writes)
                for i, ckpt in enumerate(result.checkpoints):
                    if i % 5 == 0 or i == len(result.checkpoints) - 1:
                        ckpt_record = {
                            "run_id": run_id,
                            "universe_id": result.universe_id,
                            "epoch": ckpt.epoch,
                            "mean_coherence": ckpt.stats.get("mean_coherence", 0),
                            "pct_within_bounds": ckpt.stats.get("pct_within_bounds", 0),
                            "mean_norm": ckpt.stats.get("mean_norm", 0),
                        }
                        await db.query(
                            "CREATE sim_checkpoint CONTENT $data",
                            {"data": ckpt_record},
                        )
            except Exception as e:
                logger.warning(f"DB write failed: {e}")
                self._write_jsonl("sim_universe_summary", summary)
        else:
            self._write_jsonl("sim_universe_summary", summary)

    async def store_report(self, run_id: str, report: SimulationReport) -> None:
        """Store analysis report."""
        record = {
            "run_id": run_id,
            "insights": report.insights,
            "summary": report.summary_dict(),
            "artifacts": report.artifacts,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        db = await self._get_db()
        if db:
            try:
                await db.query(
                    "CREATE sim_analysis_report CONTENT $data",
                    {"data": record},
                )
            except Exception as e:
                logger.warning(f"DB report write failed: {e}")
                self._write_jsonl("sim_analysis_report", record)
        else:
            self._write_jsonl("sim_analysis_report", record)

    async def store_journey_narrative(self, run_id: str, universe_id: str, narrative: dict) -> None:
        """Store an Ollama-generated journey narrative for a universe."""
        record = {
            "run_id": run_id,
            "universe_id": universe_id,
            "narrative": narrative.get("narrative", ""),
            "hiho_assessment": narrative.get("hiho_assessment", ""),
            "anomaly_flags": narrative.get("anomaly_flags", []),
            "population_comparison": narrative.get("population_comparison", ""),
            "model": narrative.get("model", "phi3:mini"),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        db = await self._get_db()
        if db:
            try:
                await db.query(
                    "CREATE sim_journey_narrative CONTENT $data",
                    {"data": record},
                )
            except Exception as e:
                logger.warning(f"DB narrative write failed: {e}")
                self._write_jsonl("sim_journey_narrative", record)
        else:
            self._write_jsonl("sim_journey_narrative", record)

    def _write_jsonl(self, table: str, record: dict) -> None:
        """Fallback: append record to JSONL file."""
        path = self._fallback_dir / f"{table}.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
