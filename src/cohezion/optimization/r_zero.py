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
        # Raw per-execution outcomes — the source of the trailing success rate.
        self._successes: list[bool] = []

    def record_execution(self, model_name: str, success: bool, iterations: int) -> None:
        """Record the execution pass of a local model."""
        # Trailing success rate over the last 10 executions (FIX 2026-06-06, audit §12.1).
        # The prior impl counted prior records whose DERIVED rate == 1.0 — which a fresh
        # optimizer can never produce — and divided by total+1, so base_rate never exceeded
        # 0.5 and the >0.8 difficulty branch was permanently unreachable. We now compute the
        # rate from the RAW success bools, so 10 successes → rate 1.0 → the >0.8 branch fires.
        self._successes.append(bool(success))
        window = self._successes[-10:]
        base_rate = sum(window) / len(window)

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
