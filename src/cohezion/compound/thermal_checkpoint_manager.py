"""Thermal checkpoint manager for safe 8-hour continuous execution.

Provides graceful thermal checkpoint/resume functionality to protect AMD Ryzen AI MAX+ 395
silicon during long-duration autoresearch tasks. Integrates with existing thermal monitoring
infrastructure.

Key features:
- Graceful pause at thermal thresholds (save state, cooldown, resume)
- Scheduled cooldown intervals (prevent heat soak)
- Progress persistence across thermal events
- Automatic recovery and resumption
- Integration with AutoresearchExecutor

Phase 4: 8-Hour Autoresearch Journey
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from cohezion.compound.hardware_monitor import HardwareMonitor, get_hardware_monitor
from cohezion.compound.thermal_trend_predictor import ThermalTrendPredictor


logger = logging.getLogger(__name__)


class ThermalState(Enum):
    """Thermal execution states."""

    NORMAL = auto()
    ELEVATED = auto()  # Approaching threshold
    PAUSED = auto()  # Checkpointed and cooling
    EMERGENCY = auto()  # Critical - full stop


@dataclass
class Checkpoint:
    """Represents a saved execution state."""

    timestamp: float
    task_id: str
    phase: str
    progress: dict[str, Any]
    thermal_state: ThermalState
    gpu_temp_at_checkpoint: float
    cpu_temp_at_checkpoint: float
    hypotheses_completed: int
    total_hypotheses: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThermalConfig:
    """Configuration for thermal management."""

    # Thresholds
    pause_temp: float = 90.0  # °C - pause and checkpoint
    resume_temp: float = 80.0  # °C - resume after cooling
    emergency_temp: float = 93.0  # °C - emergency stop
    elevated_temp: float = 85.0  # °C - warning zone

    # Timing
    check_interval_seconds: int = 30  # How often to check temps
    max_pause_duration_minutes: int = 30  # Max time to wait for cooling
    cooldown_interval_minutes: int = 60  # Scheduled cooldown every N minutes
    cooldown_duration_minutes: int = 5  # Duration of scheduled cooldowns

    # Persistence
    checkpoint_dir: Path = field(default_factory=lambda: Path("data/thermal_checkpoints"))
    max_checkpoints: int = 10

    # Recovery
    auto_resume: bool = True
    resume_delay_seconds: int = 60  # Wait after reaching resume_temp


class ThermalCheckpointManager:
    """Manages thermal checkpoints for long-duration execution.

    Provides graceful thermal management:
    1. Continuous thermal monitoring
    2. Predictive thermal management (30-min ahead forecasting)
    3. Scheduled cooldown intervals (prevent heat soak)
    4. Automatic checkpoint/resume at thermal boundaries
    5. Progress persistence across thermal events

    Usage:
        manager = ThermalCheckpointManager(ThermalConfig())
        async with manager.thermal_managed_execution():
            await manager.execute_with_checkpoints(long_running_task)
    """

    def __init__(self, config: ThermalConfig | None = None):
        self.config = config or ThermalConfig()
        self.monitor: HardwareMonitor = get_hardware_monitor()
        self.predictor: ThermalTrendPredictor = ThermalTrendPredictor()

        self.state = ThermalState.NORMAL
        self.current_checkpoint: Checkpoint | None = None
        self.checkpoints: list[Checkpoint] = []
        self.start_time: float = 0.0
        self.last_cooldown_time: float = 0.0
        self.total_paused_time: float = 0.0

        # Ensure checkpoint directory exists
        self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        logger.info("ThermalCheckpointManager initialized")
        logger.info(f"  Pause threshold: {self.config.pause_temp}°C")
        logger.info(f"  Resume threshold: {self.config.resume_temp}°C")
        logger.info(f"  Emergency threshold: {self.config.emergency_temp}°C")
        logger.info(f"  Cooldown interval: {self.config.cooldown_interval_minutes} min")

    async def __aenter__(self):
        """Async context manager entry."""
        self.start_time = time.time()
        self.last_cooldown_time = self.start_time
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Save final checkpoint if we have one
        if self.current_checkpoint:
            await self._persist_checkpoint(self.current_checkpoint)

    async def execute_with_checkpoints(
        self,
        task_fn: Callable[[], Coroutine[Any, Any, Any]],
        task_id: str = "8hr_autoresearch",
        total_hypotheses: int = 100,
    ) -> dict[str, Any]:
        """Execute a task with thermal checkpoint/resume protection.

        Args:
            task_fn: Async function that performs work. Should check
                    should_pause() periodically and save progress.
            task_id: Unique identifier for this execution
            total_hypotheses: Total expected work items

        Returns:
            Execution result dict with completion status and stats
        """
        logger.info(f"Starting thermal-managed execution: {task_id}")

        # Try to resume from existing checkpoint
        existing = await self._load_latest_checkpoint(task_id)
        if existing:
            logger.info(f"Resuming from checkpoint: {existing.checkpoint_id}")
            self.current_checkpoint = existing
            hypotheses_completed = existing.hypotheses_completed
        else:
            hypotheses_completed = 0
            self.current_checkpoint = Checkpoint(
                timestamp=time.time(),
                task_id=task_id,
                phase="starting",
                progress={},
                thermal_state=ThermalState.NORMAL,
                gpu_temp_at_checkpoint=0.0,
                cpu_temp_at_checkpoint=0.0,
                hypotheses_completed=0,
                total_hypotheses=total_hypotheses,
            )

        execution_stats = {
            "task_id": task_id,
            "started_at": time.time(),
            "completed_hypotheses": hypotheses_completed,
            "total_hypotheses": total_hypotheses,
            "thermal_events": [],
            "total_paused_minutes": 0.0,
            "completed": False,
            "error": None,
        }

        try:
            while hypotheses_completed < total_hypotheses:
                # Check thermal status
                should_pause, reason = await self._should_pause()

                if should_pause:
                    # Checkpoint current state
                    await self._do_checkpoint(
                        task_id=task_id,
                        phase=f"hypothesis_{hypotheses_completed}",
                        progress={"current": hypotheses_completed},
                        hypotheses_completed=hypotheses_completed,
                        total_hypotheses=total_hypotheses,
                    )

                    # Enter cooldown
                    pause_duration = await self._cooldown(reason)
                    execution_stats["thermal_events"].append(
                        {
                            "timestamp": time.time(),
                            "reason": reason,
                            "duration_minutes": pause_duration / 60,
                        }
                    )
                    execution_stats["total_paused_minutes"] += pause_duration / 60
                    self.total_paused_time += pause_duration

                    # Resume
                    logger.info(f"Resuming execution after {pause_duration / 60:.1f} min cooldown")

                # Check for scheduled cooldown
                if await self._should_do_scheduled_cooldown():
                    logger.info("Performing scheduled cooldown")
                    await self._do_checkpoint(
                        task_id=task_id,
                        phase=f"hypothesis_{hypotheses_completed}_scheduled_cooldown",
                        progress={"current": hypotheses_completed},
                        hypotheses_completed=hypotheses_completed,
                        total_hypotheses=total_hypotheses,
                    )
                    await self._scheduled_cooldown()
                    execution_stats["thermal_events"].append(
                        {
                            "timestamp": time.time(),
                            "reason": "scheduled_cooldown",
                            "duration_minutes": self.config.cooldown_duration_minutes,
                        }
                    )

                # Execute one unit of work
                try:
                    await task_fn()
                    hypotheses_completed += 1
                    execution_stats["completed_hypotheses"] = hypotheses_completed

                    # Update checkpoint periodically
                    if hypotheses_completed % 10 == 0:
                        await self._do_checkpoint(
                            task_id=task_id,
                            phase=f"hypothesis_{hypotheses_completed}",
                            progress={"current": hypotheses_completed},
                            hypotheses_completed=hypotheses_completed,
                            total_hypotheses=total_hypotheses,
                        )

                except Exception as e:
                    logger.error(f"Task execution error: {e}")
                    await self._do_checkpoint(
                        task_id=task_id,
                        phase=f"error_at_{hypotheses_completed}",
                        progress={"current": hypotheses_completed, "error": str(e)},
                        hypotheses_completed=hypotheses_completed,
                        total_hypotheses=total_hypotheses,
                    )
                    raise

            execution_stats["completed"] = True
            execution_stats["completed_at"] = time.time()
            execution_stats["duration_hours"] = (execution_stats["completed_at"] - execution_stats["started_at"]) / 3600
            execution_stats["effective_duration_hours"] = execution_stats["duration_hours"] - (
                execution_stats["total_paused_minutes"] / 60
            )

        except Exception as e:
            execution_stats["error"] = str(e)
            execution_stats["completed"] = False
            raise
        finally:
            # Final checkpoint
            await self._do_checkpoint(
                task_id=task_id,
                phase="completed" if execution_stats["completed"] else "interrupted",
                progress=execution_stats,
                hypotheses_completed=hypotheses_completed,
                total_hypotheses=total_hypotheses,
            )

        return execution_stats

    async def _should_pause(self) -> tuple[bool, str]:
        """Check if we should pause due to thermal conditions.

        Returns:
            (should_pause, reason)
        """
        metrics = self.monitor.get_current_metrics()
        gpu_temp = metrics.gpu_temp_current
        cpu_temp = metrics.cpu_temp_current

        # Check emergency first
        if gpu_temp >= self.config.emergency_temp or cpu_temp >= self.config.emergency_temp:
            self.state = ThermalState.EMERGENCY
            return True, f"EMERGENCY: GPU={gpu_temp}°C, CPU={cpu_temp}°C"

        # Check predictive (30-min ahead)
        try:
            prediction = self.predictor.predict_30min_ahead()
            if prediction and prediction.predicted_temp_c > self.config.pause_temp:
                self.state = ThermalState.ELEVATED
                return True, f"PREDICTED: {prediction.predicted_temp_c:.1f}°C in 30 min"
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")

        # Check current
        if gpu_temp >= self.config.pause_temp or cpu_temp >= self.config.pause_temp:
            self.state = ThermalState.ELEVATED
            return True, f"CURRENT: GPU={gpu_temp}°C, CPU={cpu_temp}°C"

        # Check elevated (warning but don't pause yet)
        if gpu_temp >= self.config.elevated_temp or cpu_temp >= self.config.elevated_temp:
            self.state = ThermalState.ELEVATED
            logger.warning(f"Elevated temps: GPU={gpu_temp}°C, CPU={cpu_temp}°C")
        else:
            self.state = ThermalState.NORMAL

        return False, ""

    async def _should_do_scheduled_cooldown(self) -> bool:
        """Check if it's time for a scheduled cooldown."""
        elapsed = time.time() - self.last_cooldown_time
        return elapsed >= (self.config.cooldown_interval_minutes * 60)

    async def _cooldown(self, reason: str) -> float:
        """Perform cooldown until safe temperature reached.

        Returns:
            Duration of cooldown in seconds
        """
        start_pause = time.time()
        logger.warning(f"THERMAL PAUSE: {reason}")
        logger.info(f"Cooling down until {self.config.resume_temp}°C...")

        self.state = ThermalState.PAUSED

        while True:
            await asyncio.sleep(self.config.check_interval_seconds)

            metrics = self.monitor.get_current_metrics()
            gpu_temp = metrics.gpu_temp_current
            cpu_temp = metrics.cpu_temp_current
            elapsed = time.time() - start_pause

            # Check if we've cooled enough
            if gpu_temp <= self.config.resume_temp and cpu_temp <= self.config.resume_temp:
                logger.info(f"Cooled to GPU={gpu_temp}°C, CPU={cpu_temp}°C")
                # Extra wait for stabilization
                await asyncio.sleep(self.config.resume_delay_seconds)
                break

            # Check max pause duration
            if elapsed > (self.config.max_pause_duration_minutes * 60):
                logger.warning(f"Max pause duration reached. Resuming at GPU={gpu_temp}°C")
                break

            # Log progress every minute
            if int(elapsed) % 60 == 0:
                logger.info(f"Cooling... GPU={gpu_temp}°C, CPU={cpu_temp}°C, paused for {elapsed / 60:.1f} min")

        duration = time.time() - start_pause
        self.state = ThermalState.NORMAL
        logger.info(f"Resuming after {duration / 60:.1f} minutes cooldown")

        return duration

    async def _scheduled_cooldown(self) -> None:
        """Perform a scheduled cooldown to prevent heat soak."""
        logger.info(f"Scheduled cooldown for {self.config.cooldown_duration_minutes} minutes")
        start = time.time()

        self.state = ThermalState.PAUSED
        await asyncio.sleep(self.config.cooldown_duration_minutes * 60)

        self.last_cooldown_time = time.time()
        self.state = ThermalState.NORMAL
        duration = time.time() - start

        logger.info(f"Scheduled cooldown complete: {duration / 60:.1f} minutes")

    async def _do_checkpoint(
        self,
        task_id: str,
        phase: str,
        progress: dict[str, Any],
        hypotheses_completed: int,
        total_hypotheses: int,
    ) -> None:
        """Create and persist a checkpoint."""
        metrics = self.monitor.get_current_metrics()

        checkpoint = Checkpoint(
            timestamp=time.time(),
            task_id=task_id,
            phase=phase,
            progress=progress,
            thermal_state=self.state,
            gpu_temp_at_checkpoint=metrics.gpu_temp_current,
            cpu_temp_at_checkpoint=metrics.cpu_temp_current,
            hypotheses_completed=hypotheses_completed,
            total_hypotheses=total_hypotheses,
            metadata={
                "elapsed_hours": (time.time() - self.start_time) / 3600,
                "total_paused_hours": self.total_paused_time / 3600,
            },
        )

        self.current_checkpoint = checkpoint
        self.checkpoints.append(checkpoint)

        await self._persist_checkpoint(checkpoint)

    async def _persist_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Persist checkpoint to disk."""
        checkpoint_file = self.config.checkpoint_dir / f"{checkpoint.task_id}.json"

        try:
            checkpoint_data = {
                "timestamp": checkpoint.timestamp,
                "task_id": checkpoint.task_id,
                "phase": checkpoint.phase,
                "progress": checkpoint.progress,
                "thermal_state": checkpoint.thermal_state.name,
                "gpu_temp_at_checkpoint": checkpoint.gpu_temp_at_checkpoint,
                "cpu_temp_at_checkpoint": checkpoint.cpu_temp_at_checkpoint,
                "hypotheses_completed": checkpoint.hypotheses_completed,
                "total_hypotheses": checkpoint.total_hypotheses,
                "metadata": checkpoint.metadata,
            }

            # Atomic write
            temp_file = checkpoint_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(checkpoint_data, f, indent=2)
            temp_file.rename(checkpoint_file)

            logger.debug(f"Checkpoint saved: {checkpoint_file}")

        except Exception as e:
            logger.error(f"Failed to persist checkpoint: {e}")

    async def _load_latest_checkpoint(self, task_id: str) -> Checkpoint | None:
        """Load the latest checkpoint for a task."""
        checkpoint_file = self.config.checkpoint_dir / f"{task_id}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file) as f:
                data = json.load(f)

            checkpoint = Checkpoint(
                timestamp=data["timestamp"],
                task_id=data["task_id"],
                phase=data["phase"],
                progress=data["progress"],
                thermal_state=ThermalState[data["thermal_state"]],
                gpu_temp_at_checkpoint=data["gpu_temp_at_checkpoint"],
                cpu_temp_at_checkpoint=data["cpu_temp_at_checkpoint"],
                hypotheses_completed=data["hypotheses_completed"],
                total_hypotheses=data["total_hypotheses"],
                metadata=data.get("metadata", {}),
            )

            logger.info(
                f"Loaded checkpoint: {checkpoint.phase},"
                f" {checkpoint.hypotheses_completed}/{checkpoint.total_hypotheses} completed"
            )
            return checkpoint

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def get_status(self) -> dict[str, Any]:
        """Get current thermal status."""
        metrics = self.monitor.get_current_metrics()
        elapsed = time.time() - self.start_time

        return {
            "state": self.state.name,
            "gpu_temp_c": metrics.gpu_temp_current,
            "cpu_temp_c": metrics.cpu_temp_current,
            "elapsed_hours": elapsed / 3600,
            "total_paused_minutes": self.total_paused_time / 60,
            "checkpoints_created": len(self.checkpoints),
            "next_scheduled_cooldown_min": max(
                0,
                (self.config.cooldown_interval_minutes * 60 - (time.time() - self.last_cooldown_time)) / 60,
            ),
        }


# Singleton instance
def get_thermal_checkpoint_manager(
    config: ThermalConfig | None = None,
) -> ThermalCheckpointManager:
    """Get singleton thermal checkpoint manager."""
    return ThermalCheckpointManager(config)
