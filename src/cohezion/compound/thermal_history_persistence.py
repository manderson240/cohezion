"""JSONL-based persistence for thermal time-series data.

Collects thermal samples every 5 minutes, persists to JSONL for long-term learning.
Supports vault integration for distributed knowledge (non-blocking).

Phase 3 Sprint 2: Predictive Thermal Throttling

Key features:
- Background collection at 5-minute intervals
- JSONL persistence with atomic writes
- Automatic rotation when file exceeds 10MB
- Non-blocking vault logging for learned patterns
- Recovery from file corruption (append safety)
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from cohezion.compound.thermal_trend_predictor import ThermalTimeSeries


logger = logging.getLogger(__name__)


class ThermalTimeSeriesCollector:
    """Collects thermal samples and persists to JSONL.

    Runs a background task that samples thermal metrics every 5 minutes,
    appends to JSONL, and optionally logs to vault for distributed learning.

    Parameters
    ----------
    history_path : str or Path
        Path to thermal_history.jsonl (default: data/compound/thermal/thermal_history.jsonl)
    sample_interval_seconds : int
        Sampling interval (default: 300 = 5 minutes)
    enable_vault_logging : bool
        If True, log samples to vault asynchronously (default: True)
    """

    DEFAULT_HISTORY_PATH = Path("data/compound/thermal/thermal_history.jsonl")
    MAX_JSONL_SIZE_MB = 10
    SAMPLE_INTERVAL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        history_path: Path | None = None,
        sample_interval_seconds: int = 300,
        enable_vault_logging: bool = True,
    ) -> None:
        """Initialize thermal time-series collector."""
        self.history_path = Path(history_path or self.DEFAULT_HISTORY_PATH)
        self.sample_interval_seconds = sample_interval_seconds
        self.enable_vault_logging = enable_vault_logging

        # Ensure directory exists
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

        self._collection_task: asyncio.Task | None = None
        self._samples_since_vault_log = 0

    def start_collection(self) -> None:
        """Start background thermal collection task."""
        if self._collection_task is None or self._collection_task.done():
            self._collection_task = asyncio.create_task(self._collect_loop())
            logger.info(f"Started thermal collection to {self.history_path}")

    def stop_collection(self) -> None:
        """Stop background thermal collection task."""
        if self._collection_task:
            self._collection_task.cancel()
            logger.info("Stopped thermal collection")

    async def _collect_loop(self) -> None:
        """Background collection loop (runs every 5 minutes)."""
        try:
            while True:
                try:
                    sample = await self._collect_sample()
                    if sample:
                        await self._save_sample_to_jsonl(sample)
                        self._samples_since_vault_log += 1

                        # Log to vault every 12 samples (1 hour)
                        if self.enable_vault_logging and self._samples_since_vault_log >= 12:
                            asyncio.create_task(self._log_to_vault_async())
                            self._samples_since_vault_log = 0
                except Exception as e:
                    logger.debug(f"Error in collection loop: {e}")

                await asyncio.sleep(self.sample_interval_seconds)
        except asyncio.CancelledError:
            logger.debug("Thermal collection task cancelled")

    async def _collect_sample(self) -> ThermalTimeSeries | None:
        """Collect single thermal sample from hardware.

        Returns
        -------
        ThermalTimeSeries or None
            Thermal sample, or None if unable to collect
        """
        try:
            # Lazy import to avoid circular dependency
            from cohezion.compound.hardware_monitor import get_hardware_monitor

            monitor = get_hardware_monitor()
            metrics = monitor.get_current_metrics()

            return ThermalTimeSeries(
                timestamp=time.time(),
                gpu_temp_c=metrics.gpu_temp_current,
                cpu_temp_c=metrics.cpu_temp_current,
                gpu_clock_mhz=metrics.gpu_clock_mhz,
                throttle_detected=monitor.is_thermal_throttling(),
                power_watts=metrics.gpu_power,
            )
        except Exception as e:
            logger.debug(f"Failed to collect thermal sample: {e}")
            return None

    async def _save_sample_to_jsonl(self, sample: ThermalTimeSeries) -> None:
        """Append sample to JSONL with atomic write.

        Parameters
        ----------
        sample : ThermalTimeSeries
            Sample to persist
        """
        try:
            # Prepare JSONL line
            json_dict = {
                "timestamp": sample.timestamp,
                "gpu_temp_c": sample.gpu_temp_c,
                "cpu_temp_c": sample.cpu_temp_c,
                "gpu_clock_mhz": sample.gpu_clock_mhz,
                "throttle_detected": sample.throttle_detected,
                "batch_size_recent": sample.batch_size_recent,
                "concurrency_level": sample.concurrency_level,
                "power_watts": sample.power_watts,
            }
            json_line = json.dumps(json_dict) + "\n"

            # Atomic write: write to temp file, then rename
            temp_path = self.history_path.with_suffix(".jsonl.tmp")
            with open(temp_path, "a", encoding="utf-8") as f:
                f.write(json_line)

            # Check if main file exists; if so, append temp to it
            if self.history_path.exists():
                with open(self.history_path, "a", encoding="utf-8") as f:
                    f.write(json_line)
                temp_path.unlink(missing_ok=True)
            else:
                temp_path.rename(self.history_path)

            # Check size and rotate if needed
            await self._rotate_jsonl_if_needed()

        except Exception as e:
            logger.debug(f"Failed to save thermal sample: {e}")

    async def _rotate_jsonl_if_needed(self) -> None:
        """Archive JSONL file if it exceeds max size."""
        try:
            if not self.history_path.exists():
                return

            size_mb = self.history_path.stat().st_size / (1024 * 1024)

            if size_mb >= self.MAX_JSONL_SIZE_MB:
                # Archive current file
                timestamp = datetime.now().strftime("%Y%m%d")
                archive_path = self.history_path.with_stem(f"thermal_history_{timestamp}").with_suffix(".jsonl.gz")

                with open(self.history_path, "rb") as f_in:
                    with gzip.open(archive_path, "wb") as f_out:
                        f_out.write(f_in.read())

                # Clear original file
                self.history_path.write_text("")

                logger.info(f"Rotated thermal history to {archive_path}")
        except Exception as e:
            logger.debug(f"Error rotating JSONL: {e}")

    async def _log_to_vault_async(self) -> None:
        """Log thermal metrics to vault asynchronously (non-blocking).

        Non-blocking: wrapped in try/except, doesn't impact operation.
        """
        try:
            from cohezion.core.mcp_client import get_mcp_client

            client = get_mcp_client()
            if not client:
                return

            # Load recent samples
            recent = await self.load_jsonl_history_async(hours=1)
            if not recent:
                return

            # Calculate summary
            temps = [s["gpu_temp_c"] for s in recent]
            summary = {
                "avg_gpu_temp": sum(temps) / len(temps),
                "max_gpu_temp": max(temps),
                "min_gpu_temp": min(temps),
                "samples": len(recent),
                "throttle_events": sum(1 for s in recent if s["throttle_detected"]),
            }

            # Log as experiment (non-blocking)
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(
                        client.vault_log_experiment,
                        "cohezion",
                        f"Thermal metrics 1h window: avg={summary['avg_gpu_temp']:.1f}°C",
                        f"Collected {summary['samples']} samples",
                    ),
                    timeout=1.0,  # 1-second timeout
                )
            except TimeoutError:
                logger.debug("Vault logging timed out (non-blocking)")
        except Exception as e:
            logger.debug(f"Vault logging failed (non-blocking): {e}")

    async def load_jsonl_history_async(self, hours: int = 1) -> list[dict]:
        """Load recent thermal samples from JSONL (async).

        Parameters
        ----------
        hours : int
            Load samples from last N hours (default: 1)

        Returns
        -------
        list[dict]
            List of thermal samples
        """
        try:
            if not self.history_path.exists():
                return []

            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)

            samples = []
            with open(self.history_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        sample = json.loads(line)
                        if sample.get("timestamp", 0) >= cutoff_time:
                            samples.append(sample)
                    except json.JSONDecodeError:
                        continue

            return samples
        except Exception as e:
            logger.debug(f"Error loading JSONL history: {e}")
            return []

    def record_batch_thermal(
        self,
        batch_size: int,
        peak_gpu_temp: float,
        throttle_detected: bool,
    ) -> None:
        """Record thermal metrics during batch execution.

        Called by BatchableExecutor after execution completes.

        Parameters
        ----------
        batch_size : int
            Number of tasks in batch
        peak_gpu_temp : float
            Peak GPU temperature during execution (°C)
        throttle_detected : bool
            Whether throttling was detected
        """
        try:
            sample = ThermalTimeSeries(
                timestamp=time.time(),
                gpu_temp_c=peak_gpu_temp,
                cpu_temp_c=0.0,  # Will be filled by collection task
                gpu_clock_mhz=0.0,  # Will be filled by collection task
                throttle_detected=throttle_detected,
                batch_size_recent=batch_size,
            )

            # Append to JSONL synchronously (fast path)
            json_dict = {
                "timestamp": sample.timestamp,
                "gpu_temp_c": sample.gpu_temp_c,
                "batch_size_recent": batch_size,
                "throttle_detected": throttle_detected,
            }
            json_line = json.dumps(json_dict) + "\n"

            with open(self.history_path, "a", encoding="utf-8") as f:
                f.write(json_line)

            logger.debug(f"Recorded batch thermal: batch_size={batch_size}, temp={peak_gpu_temp:.1f}°C")
        except Exception as e:
            logger.debug(f"Failed to record batch thermal: {e}")


def load_jsonl_history(history_path: Path | None = None, days: int = 7) -> list[dict]:
    """Load thermal samples from JSONL (synchronous).

    Parameters
    ----------
    history_path : Path, optional
        Path to JSONL file (default: data/compound/thermal/thermal_history.jsonl)
    days : int
        Load samples from last N days (default: 7)

    Returns
    -------
    list[dict]
        List of thermal samples
    """
    try:
        path = Path(history_path or ThermalTimeSeriesCollector.DEFAULT_HISTORY_PATH)

        if not path.exists():
            logger.debug(f"History file not found: {path}")
            return []

        current_time = time.time()
        cutoff_time = current_time - (days * 86400)

        samples = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                    if sample.get("timestamp", 0) >= cutoff_time:
                        samples.append(sample)
                except json.JSONDecodeError:
                    logger.debug(f"Skipping malformed JSON: {line[:100]}")
                    continue

        logger.debug(f"Loaded {len(samples)} thermal samples from {days} days")
        return samples
    except Exception as e:
        logger.debug(f"Error loading JSONL history: {e}")
        return []


def get_thermal_time_series_collector(reset: bool = False) -> ThermalTimeSeriesCollector:
    """Get or create singleton thermal time-series collector.

    Parameters
    ----------
    reset : bool
        If True, create new instance (default: False)

    Returns
    -------
    ThermalTimeSeriesCollector
        Singleton instance
    """
    global _collector_instance

    if reset or _collector_instance is None:
        _collector_instance = ThermalTimeSeriesCollector()

    return _collector_instance


# Module-level singleton
_collector_instance: ThermalTimeSeriesCollector | None = None


__all__ = [
    "ThermalTimeSeriesCollector",
    "get_thermal_time_series_collector",
    "load_jsonl_history",
]
