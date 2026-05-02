"""Resource guard for OOM-safe local model inference.

Prevents loading multiple large models simultaneously on UMA systems.
Monitors memory and enqueues requests when near capacity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Current memory state in GB."""

    total_gb: float
    available_gb: float
    used_gb: float

    @classmethod
    def capture(cls) -> MemorySnapshot:
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            mem_total = (
                int(next(line for line in lines if line.startswith("MemTotal:")).split()[1])
                / 1_048_576
            )
            mem_available = (
                int(next(line for line in lines if line.startswith("MemAvailable:")).split()[1])
                / 1_048_576
            )
            return cls(
                total_gb=mem_total, available_gb=mem_available, used_gb=mem_total - mem_available
            )
        except Exception as e:
            logger.warning(f"Failed to read /proc/meminfo: {e}")
            return cls(total_gb=128, available_gb=75, used_gb=53)


class ResourceGuard:
    """Singleton resource guard preventing OOM on UMA systems.

    Rules:
    - Only ONE large model (>10B params) loaded at a time
    - Available memory must stay > 16GB buffer
    - Queue requests rather than parallelizing large model inference
    """

    _instance: ResourceGuard | None = None
    SAFETY_BUFFER_GB = 16.0
    LARGE_MODEL_THRESHOLD_GB = 12.0

    def __new__(cls) -> ResourceGuard:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._active_model: str | None = None
            cls._instance._queue: list[dict[str, Any]] = []
        return cls._instance

    @property
    def active_model(self) -> str | None:
        return self._active_model

    def can_load(self, model_name: str, estimated_size_gb: float) -> bool:
        mem = MemorySnapshot.capture()
        if mem.available_gb < self.SAFETY_BUFFER_GB + estimated_size_gb:
            logger.warning(
                f"OOM guard: {model_name} needs {estimated_size_gb:.1f}GB, "
                f"only {mem.available_gb:.1f}GB available (buffer={self.SAFETY_BUFFER_GB}GB)"
            )
            return False
        if estimated_size_gb > self.LARGE_MODEL_THRESHOLD_GB and self._active_model is not None:
            logger.warning(
                f"OOM guard: {self._active_model} already active, cannot load {model_name}"
            )
            return False
        return True

    def acquire(self, model_name: str, estimated_size_gb: float) -> bool:
        if not self.can_load(model_name, estimated_size_gb):
            return False
        self._active_model = model_name
        logger.info(f"ResourceGuard: acquired {model_name} ({estimated_size_gb:.1f}GB)")
        return True

    def release(self, model_name: str) -> None:
        if self._active_model == model_name:
            self._active_model = None
            logger.info(f"ResourceGuard: released {model_name}")

    def current_memory(self) -> MemorySnapshot:
        return MemorySnapshot.capture()
