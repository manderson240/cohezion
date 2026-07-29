"""Self-Healing System - Detect drift, diagnose failures, and auto-correct."""

import contextlib

from cohezion.healing._core import (
    HEALTH_LOG_PATH,
    Corrector,
    Diagnostician,
    DiagnosisResult,
    DriftDetector,
    HealthStatus,
    SelfHealingSystem,
    get_healing_system,
)


__all__ = [
    "HEALTH_LOG_PATH",
    "HealthStatus",
    "DiagnosisResult",
    "DriftDetector",
    "Diagnostician",
    "Corrector",
    "SelfHealingSystem",
    "get_healing_system",
    "DriftAnalyzer",
    "CodeIssue",
    "DeepAuditor",
    "FileStats",
    "ActuatorSystem",
    "SelfDiagnostic",
    "VelocityMonitor",
    "AuditResult",
    "PlatformAudit",
    "analyze_utilization",
    "DistroPackage",
    "PipxPackage",
]

# Wire sibling modules into the package namespace (import-graph orphan wiring)
with contextlib.suppress(ImportError):
    from cohezion.healing.drift_analyzer import DriftAnalyzer as DriftAnalyzer

with contextlib.suppress(ImportError):
    from cohezion.healing.deep_audit import CodeIssue as CodeIssue
    from cohezion.healing.deep_audit import DeepAuditor as DeepAuditor
    from cohezion.healing.deep_audit import FileStats as FileStats

with contextlib.suppress(ImportError):
    from cohezion.healing.immune_system import ActuatorSystem as ActuatorSystem
    from cohezion.healing.immune_system import SelfDiagnostic as SelfDiagnostic
    from cohezion.healing.immune_system import VelocityMonitor as VelocityMonitor

with contextlib.suppress(ImportError):
    from cohezion.healing.platform_audit import AuditResult as AuditResult
    from cohezion.healing.platform_audit import PlatformAudit as PlatformAudit

with contextlib.suppress(ImportError):
    from cohezion.healing.utilization_audit import analyze_utilization as analyze_utilization

with contextlib.suppress(ImportError):
    from cohezion.healing.amd_s2idle_report import DistroPackage as DistroPackage
    from cohezion.healing.amd_s2idle_report import PipxPackage as PipxPackage
