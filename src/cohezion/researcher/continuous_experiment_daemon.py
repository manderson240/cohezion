"""Continuous 24/7 Experiment Execution Daemon.

Orchestrates automated local inference experiments across NPU, iGPU, CPU,
and Ollama Cloud with Preflight safety checks, FleetLock serialization,
12D FLUME manifold state vector logging, and SurrealDB / Kanban persistence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.evo_visualizer import EVOJourneyVisualizer
from cohezion.inference.fleet import route
from cohezion.inference.registry import Task
from cohezion.physics.evo_model import ExoticVacuumObject
from cohezion.researcher.daily_researcher import FleetLock, PreflightFleetCheck


logger = logging.getLogger(__name__)

# SurrealDB config
_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_NS = "cohezion"
_SURREAL_DB = "main"
_SURREAL_AUTH = "Basic cm9vdDpyb290"  # root:root


@dataclass
class ExperimentResult:
    """Dataclass representing a single 24/7 experiment run outcome."""

    experiment_id: str
    timestamp: float
    preflight_ok: bool
    npu_status: str
    igpu_status: str
    cpu_status: str
    cloud_status: str
    nodes_classified: int
    topologies: list[str]
    coherence_score: float = 0.5


class ContinuousExperimentDaemon:
    """24/7 Autonomous Experiment Daemon using local silicon and cloud models."""

    def __init__(self, fleet_lock: FleetLock | None = None) -> None:
        self.fleet_lock = fleet_lock or FleetLock()
        self.bus = EventBus()

    async def run_single_experiment(self, experiment_name: str = "247_silicon_autonomy") -> ExperimentResult:
        """Run a single safe, card-aligned experiment iteration."""
        timestamp = time.time()
        exp_id = f"exp_{int(timestamp)}"

        logger.info(f"Starting experiment {exp_id} ({experiment_name})...")

        # 1. Preflight Safety Check
        ok, reasons = PreflightFleetCheck.run()
        if not ok:
            logger.warning(f"Preflight failed for experiment {exp_id}: {reasons}")
            return ExperimentResult(
                experiment_id=exp_id,
                timestamp=timestamp,
                preflight_ok=False,
                npu_status=f"SKIPPED ({reasons})",
                igpu_status="SKIPPED",
                cpu_status="SKIPPED",
                cloud_status="SKIPPED",
                nodes_classified=0,
                topologies=[],
                coherence_score=0.0,
            )

        # 2. Acquire FleetLock for single-flight local model load protection
        async with self.fleet_lock.acquire("fleet_lock:modelload", timeout=60.0):
            # A. NPU Sensing Task
            res_npu = await route(
                f"Sensing audit for experiment {exp_id}",
                task=Task.SENSING,
                budget_usd=0.0,
            )
            npu_stat = f"OK ({res_npu.model})"

            # B. iGPU Code Gen Task
            res_igpu = await route(
                f"Code generation optimization for experiment {exp_id}",
                task=Task.CODE_GEN,
                budget_usd=0.0,
            )
            igpu_stat = f"OK ({res_igpu.model})"

            # C. CPU System Architect Task
            res_cpu = await route(
                f"Architecture stability check for experiment {exp_id}",
                task=Task.ARCHITECT,
                budget_usd=0.0,
            )
            cpu_stat = f"OK ({res_cpu.model})"

        # 3. FLUME 12D Manifold Trajectory Capture & EVO Topology Classification
        evo = ExoticVacuumObject(agent_id=f"daemon_{exp_id}", universe_id="universe-flume-247")
        evo.condense()
        actions = [
            f"Preflight safety check passed for {exp_id}",
            f"NPU sensing complete ({res_npu.model})",
            f"iGPU code generation complete ({res_igpu.model})",
            f"CPU architecture evaluation complete ({res_cpu.model})",
        ]
        viz = EVOJourneyVisualizer(output_path=f".obsidian/exp-{exp_id}-graph.json")
        graph_data = viz.process_evo(evo, actions)

        topologies = [node["topology"] for node in graph_data.get("nodes", [])]

        result = ExperimentResult(
            experiment_id=exp_id,
            timestamp=timestamp,
            preflight_ok=True,
            npu_status=npu_stat,
            igpu_status=igpu_stat,
            cpu_status=cpu_stat,
            cloud_status="STANDBY",
            nodes_classified=len(graph_data.get("nodes", [])),
            topologies=topologies,
            coherence_score=0.50,
        )

        # 4. EventBus Event Emission
        await self.bus.publish(
            Event(
                type=EventType.AGENT_COMPLETE,
                source="continuous_experiment_daemon",
                payload=asdict(result),
                priority=5,
            )
        )

        # 5. Dual Write-Through Persistence: SurrealDB + Kanban Bridge
        self._persist_surreal(result)
        self._persist_kanban(result)

        logger.info(f"Experiment {exp_id} completed successfully.")
        return result

    def _persist_surreal(self, result: ExperimentResult) -> bool:
        """SurrealDB write-through for experiment_run table."""
        surql = f"UPSERT experiment_run:{result.experiment_id} CONTENT {json.dumps(asdict(result))};"
        try:
            req = urllib.request.Request(
                _SURREAL_URL,
                data=surql.encode(),
                headers={
                    "surreal-ns": _SURREAL_NS,
                    "surreal-db": _SURREAL_DB,
                    "Content-Type": "text/plain",
                    "Authorization": _SURREAL_AUTH,
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"SurrealDB experiment_run write failed: {e}")
            return False

    def _persist_kanban(self, result: ExperimentResult) -> dict[str, Any]:
        """DataMesh Kanban persistence (SurrealDB + Obsidian Vault)."""
        kanban_item = {
            "id": f"kanban_{result.experiment_id}",
            "title": f"24/7 Experiment Run {result.experiment_id}",
            "status": "completed" if result.preflight_ok else "failed",
            "priority": "normal",
            "source": "continuous_experiment_daemon",
            "category": "autonomus_experiments",
            "details": f"NPU: {result.npu_status} | iGPU: {result.igpu_status} | CPU: {result.cpu_status} | Topologies: {result.topologies}",
        }
        return persist_item(kanban_item)

    async def run_daemon_loop(self, interval_seconds: float = 3600.0) -> None:
        """Run continuous 24/7 experiment loop with sleeping intervals."""
        logger.info(f"Starting 24/7 Continuous Experiment Daemon (Interval: {interval_seconds}s)...")
        while True:
            try:
                await self.run_single_experiment()
            except Exception as e:
                logger.error(f"Error in daemon experiment iteration: {e}", exc_info=True)
            await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cohezion 24/7 Continuous Experiment Daemon")
    parser.add_argument("--mode", choices=["once", "daemon"], default="once", help="Execution mode")
    parser.add_argument("--interval", type=float, default=3600.0, help="Interval in seconds between daemon runs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    daemon = ContinuousExperimentDaemon()
    if args.mode == "once":
        asyncio.run(daemon.run_single_experiment())
    else:
        asyncio.run(daemon.run_daemon_loop(interval_seconds=args.interval))
