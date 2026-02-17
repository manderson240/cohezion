"""Configuration and data models for the 3-tier model pool manager.

Defines tier policies (hot/warm/cold), pooled model state tracking,
and pool-level configuration with Pydantic validation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel


class ModelTierPolicy(Enum):
    """Lifecycle tier for a pooled model."""

    HOT = "hot"  # Always loaded, keep_alive=-1
    WARM = "warm"  # Loaded at startup, evictable under pressure
    COLD = "cold"  # On-demand only, evicted after timeout


@dataclass
class PooledModel:
    """Runtime state for a single model in the pool."""

    name: str
    tier: ModelTierPolicy
    size_gb: float
    loaded: bool = False
    healthy: bool = False
    last_used: float = 0.0  # 0 = never used, deterministic eviction ordering
    error_count: int = 0
    avg_latency_ms: float = 0.0

    def mark_used(self) -> None:
        """Update last-used timestamp."""
        self.last_used = time.time()

    def record_health(self, healthy: bool, latency_ms: float = 0.0) -> None:
        """Update health status and rolling latency average."""
        self.healthy = healthy
        if not healthy:
            self.error_count += 1
        else:
            self.error_count = 0
        if latency_ms > 0:
            # Exponential moving average (alpha=0.3)
            self.avg_latency_ms = 0.7 * self.avg_latency_ms + 0.3 * latency_ms


class TierConfig(BaseModel):
    """Configuration for model tier assignments and pool limits."""

    hot_models: list[str] = ["phi4-mini-reasoning:latest", "nomic-embed-text:latest"]
    warm_models: list[str] = ["glm-4.7-flash:latest", "qwen3-coder:30b"]
    cold_models: list[str] = ["deepcoder:14b", "nemotron-3-nano:latest"]
    max_concurrent_loaded: int = 4
    health_check_interval_s: float = 300.0
    memory_pressure_threshold: float = 0.80
    promotion_threshold_calls: int = 10
    cold_evict_timeout_s: float = 600.0  # 10 min idle → evict cold models


class PoolStatus(BaseModel):
    """Snapshot of current pool state."""

    loaded_models: list[str]
    healthy_models: list[str]
    total_memory_gb: float
    memory_pressure: float
    models: dict[str, dict]  # name -> PooledModel as dict
