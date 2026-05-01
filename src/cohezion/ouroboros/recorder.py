"""Ouroboros Recorder — system flight recorder with telemetry capture.

Wraps OuroborosMonitor with a runnable start/stop lifecycle that records
coherence, trajectories, and system vitals to local storage (with optional
SurrealDB persistence).
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class OuroborosRecorder:
    """Flight recorder daemon that captures system telemetry."""

    def __init__(self, interval_seconds: float = 30.0, output_dir: str | None = None):
        self.interval = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None
        self._start_time = 0.0
        self._cycle_count = 0
        self._output_dir = Path(output_dir or "data/ouroboros")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots: list[dict] = []
        self._monitor = None
        try:
            from cohezion.ouroboros.monitor import OuroborosMonitor

            self._monitor = OuroborosMonitor()
        except ImportError:
            logger.warning("OuroborosMonitor unavailable; using standalone logging")

    async def start(self) -> None:
        """Begin recording telemetry in a background loop."""
        if self._running:
            logger.warning("OuroborosRecorder already running")
            return
        self._running = True
        self._start_time = time.time()
        self._cycle_count = 0
        self._task = asyncio.create_task(self._record_loop())
        logger.info("OuroborosRecorder started (interval=%ss)", self.interval)

    async def stop(self) -> None:
        """Stop recording and persist final snapshot."""
        if not self._running:
            return
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._persist_snapshot(final=True)
        logger.info("OuroborosRecorder stopped (%d cycles)", self._cycle_count)

    async def _record_loop(self) -> None:
        """Core recording loop — captures system vitals + SurrealDB trajectories."""

        while self._running:
            try:
                self._cycle_count += 1
                snapshot = self._capture_vitals()
                # Try to enrich with SurrealDB trajectories
                if self._monitor and self._cycle_count % 2 == 0:
                    try:
                        trajectories = await self._monitor.fetch_recent_trajectories(limit=10)
                        snapshot["trajectories"] = trajectories
                        snapshot["trajectory_count"] = len(trajectories)
                    except Exception as e:
                        snapshot["trajectory_error"] = str(e)
                self.snapshots.append(snapshot)
                # Persist incrementally
                if self._cycle_count % 10 == 0:
                    self._persist_snapshot()
                logger.debug("Ouroboros cycle %d: coherence=%.3f, cpu=%.1f%%", self._cycle_count, snapshot.get("coherence", 0), snapshot["cpu_percent"])
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Ouroboros cycle %d error: %s", self._cycle_count, e)
                await asyncio.sleep(self.interval)

    def _capture_vitals(self) -> dict:
        """Capture current system vitals."""
        import os

        import psutil

        proc = psutil.Process(os.getppid())
        vm = psutil.virtual_memory()
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "cycle": self._cycle_count,
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_available_mb": vm.available / (1024 * 1024),
            "memory_percent": vm.percent,
            "process_cpu_percent": proc.cpu_percent(),
            "process_memory_mb": proc.memory_info().rss / (1024 * 1024),
            "coherence": 0.5,  # Placeholder — would query FLUME real coherence
        }
        # GPU if available
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                snapshot["gpu_percent"] = float(parts[0]) if parts else 0.0
                snapshot["gpu_memory_mb"] = float(parts[1]) if len(parts) > 1 else 0.0
        except Exception:
            pass
        return snapshot

    def _persist_snapshot(self, *, final: bool = False) -> None:
        """Write snapshots to local JSON storage."""
        if not self.snapshots:
            return
        suffix = "final" if final else f"batch_{self._cycle_count}"
        path = self._output_dir / f"ouroboros_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}.json"
        try:
            with open(path, "w") as f:
                json.dump(
                    {
                        "meta": {
                            "cycles": self._cycle_count,
                            "duration_seconds": time.time() - self._start_time,
                            "final": final,
                        },
                        "snapshots": self.snapshots[-100:],  # Keep last 100 in RAM
                    },
                    f,
                    indent=2,
                )
            logger.debug("Persisted %d snapshots to %s", len(self.snapshots), path)
        except Exception as e:
            logger.warning("Failed to persist ouroboros snapshot: %s", e)
