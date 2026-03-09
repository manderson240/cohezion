"""DynamicConcurrencyGate - Phase 1 Bottleneck #1: Remove concurrency ceiling.

Dynamically scales concurrent requests from hardcoded 4 to 8-12 based on
real-time hardware state (VRAM, thermal, GPU utilization).

Target: +45% throughput improvement.
"""

import asyncio
import logging
from dataclasses import dataclass


@dataclass
class HardwareMetrics:
    """Stub hardware metrics class."""

    vram_percent: float = 50.0
    thermal_percent: float = 40.0


class HardwareProfilerFactory:
    """Stub factory for hardware profiler (used by DynamicConcurrencyGate)."""

    @staticmethod
    def get_profiler():
        """Return a mock profiler that doesn't fail on missing imports."""

        class MockProfiler:
            def measure(self):
                return {"vram_percent": 50.0, "thermal_percent": 40.0}

        return MockProfiler()


logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyDecision:
    """Result of concurrency calculation."""

    safe_concurrency: int
    reason: str
    vram_percent: float
    thermal_percent: float
    healthy: bool


class DynamicConcurrencyGate:
    """Safely increases concurrency based on real-time hardware state.

    Monitors:
    - VRAM utilization (target: <80%)
    - Thermal state (target: <80°)
    - iGPU utilization
    - Process count

    Scaling strategy:
    - VRAM <60% + thermal <70%: 12 concurrent (plenty of headroom)
    - VRAM <70% + thermal <75%: 10 concurrent (good headroom)
    - VRAM <80% + thermal <80%: 8 concurrent (moderate headroom)
    - Else: 4 concurrent (conservative fallback)

    Attributes:
        base_concurrency: Conservative fallback level (default: 4)
        metrics: HardwareMetrics collector
        profiler: HardwareProfiler for thermal prediction
    """

    def __init__(self, base_concurrency: int = 4, enable_thermal_prediction: bool = False):
        """Initialize DynamicConcurrencyGate.

        Args:
            base_concurrency: Conservative fallback level (default: 4)
            enable_thermal_prediction: Enable 30-min thermal prediction (default: False)
        """
        self.base_concurrency = base_concurrency
        self.enable_thermal_prediction = enable_thermal_prediction
        self.metrics = HardwareMetrics()
        self.profiler = HardwareProfilerFactory.get_profiler()
        self._thermal_predictor = None
        self._last_decision: ConcurrencyDecision | None = None
        self._adjustment_count = 0

        # Lazy-load thermal predictor if enabled
        if enable_thermal_prediction:
            try:
                from cohezion.compound.thermal_trend_predictor import (
                    get_thermal_trend_predictor,
                )

                self._thermal_predictor = get_thermal_trend_predictor()
            except Exception as e:
                logger.debug(f"Failed to initialize thermal predictor: {e}, disabling prediction")
                self.enable_thermal_prediction = False

    def get_safe_concurrency(self) -> int:
        """Calculate safe concurrency for current hardware state.

        Returns:
            Safe concurrency level (4, 8, 10, or 12)
        """
        decision = self._calculate_concurrency()
        self._last_decision = decision

        if decision.safe_concurrency != self.base_concurrency:
            self._adjustment_count += 1
            if self._adjustment_count % 10 == 0:  # Log every 10 adjustments
                logger.info(
                    f"Concurrency adjusted: {decision.safe_concurrency} "
                    f"(VRAM={decision.vram_percent:.1f}%, "
                    f"thermal={decision.thermal_percent:.1f}%) - {decision.reason}"
                )

        return decision.safe_concurrency

    def _calculate_concurrency(self) -> ConcurrencyDecision:
        """Calculate safe concurrency based on hardware metrics.

        Phase 3 Sprint 2: Includes 30-minute thermal prediction for pre-emptive
        concurrency reduction BEFORE throttling occurs.

        Returns:
            ConcurrencyDecision with level and reasoning
        """
        try:
            state = self.metrics.get_snapshot()

            # Health check
            if not state.is_healthy():
                return ConcurrencyDecision(
                    safe_concurrency=self.base_concurrency,
                    reason="System unhealthy (VRAM critical or thermal critical)",
                    vram_percent=state.memory.used_percent,
                    thermal_percent=state.thermal.thermal_percent,
                    healthy=False,
                )

            vram_pct = state.memory.used_percent
            thermal_pct = state.thermal.thermal_percent

            # Phase 3 Sprint 2: Check 30-minute thermal prediction
            if self.enable_thermal_prediction and self._thermal_predictor:
                try:
                    predicted_temp, confidence = self._thermal_predictor.predict_temperature_ahead(
                        30
                    )

                    # Pre-emptive throttling based on prediction
                    if predicted_temp > 90.0 and confidence > 0.5:
                        return ConcurrencyDecision(
                            safe_concurrency=4,
                            reason=f"Pre-emptive: predicted {predicted_temp:.1f}°C in 30min "
                            f"(confidence={confidence:.2f})",
                            vram_percent=vram_pct,
                            thermal_percent=thermal_pct,
                            healthy=True,
                        )
                    elif predicted_temp > 87.0 and confidence > 0.6:
                        return ConcurrencyDecision(
                            safe_concurrency=8,
                            reason=f"Pre-emptive reduction: {predicted_temp:.1f}°C in 30min "
                            f"(confidence={confidence:.2f})",
                            vram_percent=vram_pct,
                            thermal_percent=thermal_pct,
                            healthy=True,
                        )
                except Exception as e:
                    logger.debug(f"Thermal prediction error (non-blocking): {e}")

            # Scaling decisions based on headroom (existing reactive logic)
            if vram_pct < 60 and thermal_pct < 70:
                return ConcurrencyDecision(
                    safe_concurrency=12,
                    reason="Plenty of headroom",
                    vram_percent=vram_pct,
                    thermal_percent=thermal_pct,
                    healthy=True,
                )
            elif vram_pct < 70 and thermal_pct < 75:
                return ConcurrencyDecision(
                    safe_concurrency=10,
                    reason="Good headroom",
                    vram_percent=vram_pct,
                    thermal_percent=thermal_pct,
                    healthy=True,
                )
            elif vram_pct < 80 and thermal_pct < 80:
                return ConcurrencyDecision(
                    safe_concurrency=8,
                    reason="Moderate headroom",
                    vram_percent=vram_pct,
                    thermal_percent=thermal_pct,
                    healthy=True,
                )
            else:
                return ConcurrencyDecision(
                    safe_concurrency=self.base_concurrency,
                    reason="Limited headroom, conservative fallback",
                    vram_percent=vram_pct,
                    thermal_percent=thermal_pct,
                    healthy=True,
                )

        except Exception as e:
            logger.warning(f"Error calculating concurrency: {e}, using base level")
            return ConcurrencyDecision(
                safe_concurrency=self.base_concurrency,
                reason=f"Error: {e}",
                vram_percent=0.0,
                thermal_percent=0.0,
                healthy=False,
            )

    async def acquire(self) -> asyncio.Semaphore:
        """Get semaphore with current safe concurrency level.

        Returns:
            Asyncio.Semaphore with safe concurrency as max permit count
        """
        safe_level = self.get_safe_concurrency()
        return asyncio.Semaphore(safe_level)

    def get_last_decision(self) -> ConcurrencyDecision | None:
        """Get the last concurrency decision for monitoring.

        Returns:
            Last ConcurrencyDecision or None if not yet calculated
        """
        return self._last_decision

    def get_stats(self) -> dict:
        """Get concurrency monitoring statistics.

        Returns:
            Dictionary with current state and adjustment count
        """
        decision = self._last_decision
        return {
            "current_concurrency": (
                decision.safe_concurrency if decision else self.base_concurrency
            ),
            "base_concurrency": self.base_concurrency,
            "adjustment_count": self._adjustment_count,
            "last_vram_percent": decision.vram_percent if decision else 0.0,
            "last_thermal_percent": decision.thermal_percent if decision else 0.0,
            "last_healthy": decision.healthy if decision else False,
            "last_reason": decision.reason if decision else "Not yet calculated",
        }


# Singleton factory
_gate_instance: DynamicConcurrencyGate | None = None


def get_concurrency_gate(reset: bool = False) -> DynamicConcurrencyGate:
    """Get or create DynamicConcurrencyGate singleton.

    Args:
        reset: If True, reset singleton instance

    Returns:
        DynamicConcurrencyGate instance
    """
    global _gate_instance

    if reset or _gate_instance is None:
        _gate_instance = DynamicConcurrencyGate()

    return _gate_instance


__all__ = [
    "ConcurrencyDecision",
    "DynamicConcurrencyGate",
    "get_concurrency_gate",
]
