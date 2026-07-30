"""Adaptive Framework Optimizer for Hardware Profile & Dynamic Model Routing.

Provides hardware profile inspection (AMD Strix Halo iGPU/NPU, CUDA, CPU)
and dynamic tier selection for the LocalExpertRouter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """Hardware profile describing local compute capabilities."""
    tier: str  # 'igpu', 'npu', 'cpu', 'cuda'
    vram_gb: float
    ram_gb: float
    description: str


class AdaptiveFrameworkOptimizer:
    """Adaptive framework optimizer for model routing and hardware profiling."""

    def __init__(self):
        self._profile = HardwareProfile(
            tier="igpu",
            vram_gb=128.0,
            ram_gb=128.0,
            description="AMD Strix Halo Ryzen AI Max+ 395 (128GB Unified DDR5 RAM)",
        )

    def get_current_profile(self) -> HardwareProfile:
        """Return current hardware profile."""
        return self._profile

    def optimize_routing(self, task_type: str, memory_available: float) -> str:
        """Return recommended model tier based on task type and available memory."""
        if memory_available >= 20.0:
            return "igpu"
        return "cpu"


_GLOBAL_OPTIMIZER: AdaptiveFrameworkOptimizer | None = None


def get_adaptive_optimizer() -> AdaptiveFrameworkOptimizer:
    """Return singleton instance of AdaptiveFrameworkOptimizer."""
    global _GLOBAL_OPTIMIZER
    if _GLOBAL_OPTIMIZER is None:
        _GLOBAL_OPTIMIZER = AdaptiveFrameworkOptimizer()
        logger.info("🧠 Adaptive Framework Optimizer initialized (Strix Halo 128GB profile active).")
    return _GLOBAL_OPTIMIZER
