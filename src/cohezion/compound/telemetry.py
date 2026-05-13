"""Compound loop telemetry and observability.

Provides structured logging, metrics collection, and telemetry emission
for the 11-step compound pipeline without external dependencies.

Usage:
    from cohezion.compound.telemetry import CompoundTelemetry

    telemetry = CompoundTelemetry()
    with telemetry.span("compound_pipeline", request_id="abc-123"):
        # Run compound pipeline
        result = await executor.execute(...)
        telemetry.record_step("vault_query", latency_ms=50, tokens=100)
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class StepMetrics:
    """Metrics for a single compound pipeline step."""

    step_name: str
    start_time: float
    end_time: float = 0.0
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    coherence: float = 0.0
    cache_hit: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def finalize(self) -> None:
        """Finalize metrics after step completes."""
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000


@dataclass
class PipelineMetrics:
    """Complete metrics for a compound pipeline execution."""

    request_id: str
    start_time: float
    skill_name: str = ""
    total_steps: int = 11  # Standard compound pipeline has 11 steps
    steps: list[StepMetrics] = field(default_factory=list)
    end_time: float = 0.0
    total_latency_ms: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    success: bool = False
    inflection_detected: bool = False
    vault_logged: bool = False

    def finalize(self) -> None:
        """Finalize pipeline metrics."""
        self.end_time = time.time()
        self.total_latency_ms = (self.end_time - self.start_time) * 1000
        self.total_tokens_in = sum(s.tokens_in for s in self.steps)
        self.total_tokens_out = sum(s.tokens_out for s in self.steps)


class CompoundTelemetry:
    """Telemetry collector for compound pipeline execution.

    Tracks:
    - Step-by-step latency
    - Token usage per step
    - HIHO coherence scores
    - Cache hit rates
    - Inflection points
    - Vault persistence success
    """

    STEP_NAMES = [
        "alignment_gate",  # 1. Request alignment check
        "vault_query",  # 2. Query vault for experience
        "skill_selection",  # 3. Select appropriate skill
        "guardrail_check",  # 4. Run security guardrails
        "execution",  # 5. Execute task
        "inflection_detect",  # 6. Detect inflection points
        "vault_log",  # 7. Log to vault
        "metrics_collect",  # 8. Collect metrics
        "pattern_extract",  # 9. Extract patterns
        "skill_refinement",  # 10. Refine skills (async)
        "retrospection",  # 11. Retrospective analysis
    ]

    def __init__(self, output_dir: Path | None = None):
        """Initialize telemetry.

        Args:
            output_dir: Directory to write telemetry JSON files.
                       Defaults to .telemetry/ in project root.
        """
        self.output_dir = output_dir or Path(".telemetry")
        self.output_dir.mkdir(exist_ok=True)
        self._current_pipeline: PipelineMetrics | None = None
        self._current_step: StepMetrics | None = None

    @contextmanager
    def span(self, operation: str, request_id: str, skill_name: str = "") -> Generator[None, None, None]:
        """Context manager for pipeline span.

        Usage:
            with telemetry.span("compound_pipeline", request_id="abc"):
                result = await executor.execute(...)
        """
        self._current_pipeline = PipelineMetrics(request_id=request_id, start_time=time.time(), skill_name=skill_name)

        logger.info(f"[telemetry] Pipeline {operation} started: {request_id}")

        try:
            yield
            self._current_pipeline.success = True
        except Exception as e:
            self._current_pipeline.success = False
            logger.error(f"[telemetry] Pipeline failed: {e}")
            raise
        finally:
            self._current_pipeline.finalize()
            self._emit_metrics()
            self._current_pipeline = None

    def start_step(self, step_name: str) -> None:
        """Start tracking a pipeline step."""
        if not self._current_pipeline:
            logger.warning("[telemetry] No active pipeline, step tracking skipped")
            return

        self._current_step = StepMetrics(step_name=step_name, start_time=time.time())
        logger.debug(f"[telemetry] Step started: {step_name}")

    def end_step(self, **kwargs: Any) -> None:
        """End current step with metrics.

        Args:
            **kwargs: Additional metrics (tokens_in, tokens_out, coherence, etc.)
        """
        if not self._current_step or not self._current_pipeline:
            logger.warning("[telemetry] No active step to end")
            return

        self._current_step.finalize()

        # Update with provided metrics
        for key, value in kwargs.items():
            if hasattr(self._current_step, key):
                setattr(self._current_step, key, value)

        self._current_pipeline.steps.append(self._current_step)

        logger.debug(f"[telemetry] Step ended: {self._current_step.step_name} ({self._current_step.latency_ms:.1f}ms)")

        self._current_step = None

    def record_inflection(self, detected: bool, reason: str = "") -> None:
        """Record inflection point detection."""
        if self._current_pipeline:
            self._current_pipeline.inflection_detected = detected
            logger.info(f"[telemetry] Inflection detected: {detected} - {reason}")

    def record_vault_log(self, success: bool) -> None:
        """Record vault logging success/failure."""
        if self._current_pipeline:
            self._current_pipeline.vault_logged = success
            logger.debug(f"[telemetry] Vault logged: {success}")

    def get_current_metrics(self) -> PipelineMetrics | None:
        """Get metrics for current pipeline."""
        return self._current_pipeline

    def _emit_metrics(self) -> None:
        """Emit metrics to log and file."""
        if not self._current_pipeline:
            return

        metrics = self._current_pipeline

        # Log summary
        logger.info(
            f"[telemetry] Pipeline complete: {metrics.request_id} "
            f"success={metrics.success} "
            f"latency_ms={metrics.total_latency_ms:.1f} "
            f"tokens={metrics.total_tokens_in}+{metrics.total_tokens_out} "
            f"steps={len(metrics.steps)}/11"
        )

        # Write to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{metrics.request_id[:8]}.json"
        filepath = self.output_dir / filename

        data = {
            "request_id": metrics.request_id,
            "skill_name": metrics.skill_name,
            "timestamp": datetime.now().isoformat(),
            "success": metrics.success,
            "total_latency_ms": metrics.total_latency_ms,
            "total_tokens_in": metrics.total_tokens_in,
            "total_tokens_out": metrics.total_tokens_out,
            "steps_count": len(metrics.steps),
            "inflection_detected": metrics.inflection_detected,
            "vault_logged": metrics.vault_logged,
            "steps": [
                {
                    "step_name": s.step_name,
                    "latency_ms": s.latency_ms,
                    "tokens_in": s.tokens_in,
                    "tokens_out": s.tokens_out,
                    "coherence": s.coherence,
                    "cache_hit": s.cache_hit,
                    "error": s.error,
                }
                for s in metrics.steps
            ],
        }

        try:
            filepath.write_text(json.dumps(data, indent=2))
            logger.debug(f"[telemetry] Metrics written to {filepath}")
        except Exception as e:
            logger.warning(f"[telemetry] Failed to write metrics: {e}")


# Global instance for convenience
_telemetry_instance: CompoundTelemetry | None = None


def get_telemetry(output_dir: Path | None = None) -> CompoundTelemetry:
    """Get or create global telemetry instance."""
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = CompoundTelemetry(output_dir)
    return _telemetry_instance
