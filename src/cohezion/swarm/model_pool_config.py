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

    # HOT tier: Always loaded, keep_alive=-1 (OOM-safe: <5GB total)
    # Strategy: Tiny specialists for instant-response tasks
    hot_models: list[str] = [
        "phi3:mini",  # 2.2GB - general reasoning, function calling
        "nomic-embed-text:latest",  # 274MB - embeddings (classic)
        "gemini-embedding-2:latest",  # ~1GB - Gemini Embedding 2.0 (Mar 2026)
        "lfm2.5-thinking:latest",  # 731MB - fast reasoning
        "nemotron-cascade-2:latest",  # 1.76GB - NVIDIA cascade (fast)
    ]

    # WARM tier: Loaded at startup, evictable under pressure (~20GB budget)
    # Strategy: Quality specialists that handle 80% of tasks without cloud
    warm_models: list[str] = [
        # Math specialists (reasoning-heavy)
        "qwen2-math:7b",  # 4.4GB - mathematical reasoning
        "mathstral:7b",  # 4.1GB - Mistral math variant

        # Code specialists
        "qwen2.5-coder:7b",  # 4.7GB - general code generation
        "ministral-3:3b",  # 3.0GB - small Mistral, multilingual

        # Vision + multimodal
        "moondream:latest",  # 1.7GB - vision understanding (charts, diagrams)
    ]

    # COLD tier: On-demand only, evicted after timeout (large models + cloud)
    # Strategy: High-quality fallbacks when WARM tier insufficient
    cold_models: list[str] = [
        # Large local models (10-30GB range)
        "deepcoder:14b",  # 9.0GB - deep code understanding
        "phi4:latest",  # 9.1GB - advanced reasoning (14B-quality in 9GB)
        "qwen2.5-coder:14b",  # 9.0GB - advanced code generation
        "gpt-oss:20b",  # 13GB - OpenAI-style reasoning
        "devstral-small-2:24b",  # 15GB - Mistral dev variant
        "glm-4.7-flash:latest",  # 19GB - fast Chinese + English
        "nemotron-3-nano:30b",  # 24GB - NVIDIA research model (high quality)

        # Cloud models (zero memory, API cost)
        "minimax-m2.7:cloud",  # Cloud fallback
        "qwen3.5:cloud",  # Qwen3.5 latest (Feb 2026)
        "qwen3.5:397b-cloud",  # Qwen3.5 max performance
        "glm-5:cloud",  # GLM-5 cloud
        "nemotron-3-super:cloud",  # Nemotron Super 120B
        "kimi-k2.5:cloud",  # Kimi K2.5 (March 2026)
        "qwen3-coder-next:cloud",  # Qwen3 Coder MoE
    ]

    # Memory safety: With other sessions running, limit concurrent loaded models
    max_concurrent_loaded: int = 3  # Reduced from 4 for OOM safety
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
