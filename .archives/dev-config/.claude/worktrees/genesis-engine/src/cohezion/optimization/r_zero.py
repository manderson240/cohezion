"""R-Zero optimization metrics connected to local models."""

from __future__ import annotations

import logging

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class RZeroMetrics(BaseModel):
    """Track metrics for compound engineering success rates."""

    success_rate: float
    iteration_count: int
    difficulty_adjustment: float


class LocalModelOptimizer:
    """Connects R-Zero metrics to local Ollama models (Qwen3-Coder, DeepSeek-R1)."""

    def __init__(self) -> None:
        self.metrics_history: list[RZeroMetrics] = []

    def record_execution(self, model_name: str, success: bool, iterations: int) -> None:
        """Record the execution pass of a local model."""
        # Calculate trailing success rate
        recent_successes = sum(1 for m in self.metrics_history[-10:] if m.success_rate == 1.0)
        total = min(10, max(1, len(self.metrics_history)))

        base_rate = (recent_successes + (1 if success else 0)) / (total + 1)

        metrics = RZeroMetrics(
            success_rate=base_rate,
            iteration_count=iterations,
            difficulty_adjustment=1.0 if base_rate > 0.8 else 0.8,
        )
        self.metrics_history.append(metrics)
        logger.info(
            f"R-Zero metrics updated for {model_name}: SR={base_rate:.2f}, Iter={iterations}"
        )

    def get_current_multiplier(self) -> float:
        """Get the current difficulty multiplier based on R-Zero metrics."""
        if not self.metrics_history:
            return 1.0
        return self.metrics_history[-1].difficulty_adjustment
