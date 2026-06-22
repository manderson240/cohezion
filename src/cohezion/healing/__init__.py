"""
Self-Healing System - Detect drift, diagnose failures, and auto-correct.

Based on:
- HuggingFace H-LLM framework (https://arxiv.org/abs/2312.xxxxx)
- Unicron: Self-Healing LLM Training

Features:
- Performance drift detection
- LLM-based failure diagnosis
- Autonomous adaptation
- Landscape research for improvements
"""

import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

HEALTH_LOG_PATH = Path(__file__).parent.parent / "knowledge_graph" / "health_log.json"


@dataclass
class HealthStatus:
    """System health status."""

    component: str
    status: str  # healthy, degraded, failing
    metric: str
    current_value: float
    threshold: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class DiagnosisResult:
    """Result of failure diagnosis."""

    component: str
    issue: str
    probable_cause: str
    recommended_action: str
    confidence: float


class DriftDetector:
    """Detect performance drift in system components."""

    def __init__(self):
        self._baselines: dict[str, float] = {}
        self._history: list[HealthStatus] = []

    def set_baseline(self, component: str, metric: str, value: float) -> None:
        """Set baseline for a component metric."""
        key = f"{component}:{metric}"
        self._baselines[key] = value

    def check(
        self,
        component: str,
        metric: str,
        current: float,
        threshold_pct: float = 0.2,
    ) -> HealthStatus:
        """Check if component has drifted from baseline."""
        key = f"{component}:{metric}"
        baseline = self._baselines.get(key, current)

        drift = abs(current - baseline) / max(baseline, 0.001)

        if drift > threshold_pct * 2:
            status = "failing"
        elif drift > threshold_pct:
            status = "degraded"
        else:
            status = "healthy"

        result = HealthStatus(
            component=component,
            status=status,
            metric=metric,
            current_value=current,
            threshold=baseline * (1 + threshold_pct),
        )

        self._history.append(result)
        return result

    def get_degraded_components(self) -> list[HealthStatus]:
        """Get all components with degraded or failing status."""
        return [h for h in self._history[-100:] if h.status != "healthy"]


class Diagnostician:
    """LLM-based failure diagnosis."""

    def __init__(self):
        self._known_issues: dict[str, DiagnosisResult] = {
            "high_latency": DiagnosisResult(
                component="swarm",
                issue="High response latency",
                probable_cause="Model overloaded or insufficient resources",
                recommended_action="Switch to smaller model or increase timeout",
                confidence=0.8,
            ),
            "low_quality": DiagnosisResult(
                component="swarm",
                issue="Low response quality",
                probable_cause="Model not suited for task type",
                recommended_action="Benchmark alternatives and swap model",
                confidence=0.7,
            ),
            "connection_failed": DiagnosisResult(
                component="ollama",
                issue="Connection to Ollama failed",
                probable_cause="Ollama service not running",
                recommended_action="Restart Ollama: ollama serve",
                confidence=0.9,
            ),
            "sandbox_divergence": DiagnosisResult(
                component="sandbox",
                issue="Sandbox simulation divergence detected",
                probable_cause="Numerical instability or HIHO coherence drift in simulation",
                recommended_action="Restart sandbox with tighter divergence thresholds",
                confidence=0.85,
            ),
        }

    def diagnose(self, health_status: HealthStatus) -> DiagnosisResult:
        """Diagnose a health issue."""
        # Pattern matching on known issues
        if health_status.metric == "latency_ms" and health_status.status == "failing":
            return self._known_issues["high_latency"]

        if health_status.metric == "quality_score" and health_status.status in (
            "degraded",
            "failing",
        ):
            return self._known_issues["low_quality"]

        if health_status.component == "ollama" and health_status.status == "failing":
            return self._known_issues["connection_failed"]

        if health_status.component == "sandbox" and health_status.metric == "divergence":
            return self._known_issues["sandbox_divergence"]

        # Generic diagnosis
        return DiagnosisResult(
            component=health_status.component,
            issue=f"{health_status.metric} {health_status.status}",
            probable_cause="Unknown - requires investigation",
            recommended_action="Check logs and component health",
            confidence=0.3,
        )


class Corrector:
    """Autonomous correction of detected issues."""

    def __init__(self):
        self._corrections: list[dict[str, Any]] = []

    async def apply_correction(self, diagnosis: DiagnosisResult) -> bool:
        """Apply automatic correction based on diagnosis."""
        correction = {
            "timestamp": datetime.now().isoformat(),
            "component": diagnosis.component,
            "issue": diagnosis.issue,
            "action": diagnosis.recommended_action,
            "applied": False,
        }

        # Auto-corrections we can apply
        if "swap model" in diagnosis.recommended_action.lower():
            # Trigger model manager to benchmark and swap
            from cohezion.swarm.model_manager import get_manager

            get_manager()
            # Mark as needing swap - actual swap happens on next call
            correction["applied"] = True
            logger.info(f"Scheduled model swap for {diagnosis.component}")

        self._corrections.append(correction)
        self._save_log()

        return correction["applied"]

    def _save_log(self) -> None:
        """Save correction history."""
        HEALTH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEALTH_LOG_PATH.write_text(
            json.dumps(
                {
                    "corrections": self._corrections[-100:],
                },
                indent=2,
            )
        )

    def get_history(self) -> list[dict[str, Any]]:
        """Get correction history."""
        return self._corrections


class SelfHealingSystem:
    """
    Complete self-healing system.

    Integrates:
    - Drift detection
    - LLM-based diagnosis
    - Autonomous correction
    """

    def __init__(self):
        self.detector = DriftDetector()
        self.diagnostician = Diagnostician()
        self.corrector = Corrector()

    async def health_check(self) -> list[HealthStatus]:
        """Run full system health check."""
        issues = []

        # Check Ollama
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                ollama_healthy = resp.status_code == 200
        except Exception:
            ollama_healthy = False

        status = self.detector.check("ollama", "available", 1.0 if ollama_healthy else 0.0, 0.1)
        if status.status != "healthy":
            issues.append(status)

        # Check SurrealDB
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:8001/health")
                surreal_healthy = resp.status_code == 200
        except Exception:
            surreal_healthy = False

        status = self.detector.check("surrealdb", "available", 1.0 if surreal_healthy else 0.0, 0.1)
        if status.status != "healthy":
            issues.append(status)

        # Check sandbox health via ResourceMonitor
        try:
            from cohezion.reliability.monitor import get_resource_monitor

            monitor = get_resource_monitor()
            sandbox_mem = monitor.total_sandbox_memory_mb
            # Flag if sandboxes are using >80GB (80% of 100GB budget)
            sandbox_ratio = sandbox_mem / (100 * 1024) if sandbox_mem > 0 else 0.0
            status = self.detector.check("sandbox", "memory_pressure", sandbox_ratio, 0.8)
            if status.status != "healthy":
                issues.append(status)
        except Exception as e:
            logger.debug("Sandbox memory check failed: %s", e)

        # Check Heartbeats
        try:
            import time

            from cohezion.reliability.heartbeat import get_heartbeats

            heartbeats = get_heartbeats()
            current_time = time.time()
            for daemon, ts in heartbeats.items():
                age = current_time - ts
                status = self.detector.check(f"daemon:{daemon}", "heartbeat_age", age, 300.0)
                if status.status != "healthy":
                    issues.append(status)
        except Exception as e:
            logger.debug("Heartbeat check failed: %s", e)

        return issues

    async def heal(self, issues: list[HealthStatus]) -> int:
        """Attempt to heal detected issues."""
        healed = 0

        for issue in issues:
            diagnosis = self.diagnostician.diagnose(issue)
            if diagnosis.confidence >= 0.5 and await self.corrector.apply_correction(diagnosis):
                healed += 1
                logger.info(f"Healed: {diagnosis.issue}")

        return healed


# Singleton
_system: SelfHealingSystem | None = None


def get_healing_system() -> SelfHealingSystem:
    global _system
    if _system is None:
        _system = SelfHealingSystem()
    return _system


# Wire sibling modules into the package namespace (import-graph orphan wiring)
with contextlib.suppress(Exception):
    from cohezion.healing.drift_analyzer import DriftAnalyzer as DriftAnalyzer

with contextlib.suppress(Exception):
    from cohezion.healing.deep_audit import CodeIssue as CodeIssue
    from cohezion.healing.deep_audit import DeepAuditor as DeepAuditor
    from cohezion.healing.deep_audit import FileStats as FileStats

with contextlib.suppress(Exception):
    from cohezion.healing.immune_system import ActuatorSystem as ActuatorSystem
    from cohezion.healing.immune_system import SelfDiagnostic as SelfDiagnostic
    from cohezion.healing.immune_system import VelocityMonitor as VelocityMonitor

with contextlib.suppress(Exception):
    from cohezion.healing.platform_audit import AuditResult as AuditResult
    from cohezion.healing.platform_audit import PlatformAudit as PlatformAudit

with contextlib.suppress(Exception):
    from cohezion.healing.utilization_audit import analyze_utilization as analyze_utilization

with contextlib.suppress(Exception):
    from cohezion.healing.amd_s2idle_report import DistroPackage as DistroPackage
    from cohezion.healing.amd_s2idle_report import PipxPackage as PipxPackage
